"""SSRF guard for recipe import, read-only admin SQL console, Stripe webhook trust."""

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import httpcore
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.user import User
from app.services.admin_service import AdminQueryForbiddenError, AdminService
from app.services.ai.recipe_import.service import RecipeImportFetchError, RecipeImportService
from app.services.stripe_webhook_service import StripeWebhookService


def _resolves_to(*addresses):
    return patch(
        "app.services.ai.recipe_import.service.socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, 0)) for a in addresses],
    )


class TestRecipeImportSsrf:
    @pytest.mark.parametrize(
        "url",
        [
            "http://api.railway.internal:8000/",
            "https://printer.local/",
            "http://127.0.0.1/",
            "http://[::1]/",
            "http://169.254.169.254/latest/meta-data",
        ],
    )
    def test_private_targets_rejected_without_lookup(self, url):
        with pytest.raises(RecipeImportFetchError):
            RecipeImportService._validate_url(url)

    def test_hostname_resolving_to_private_ip_is_rejected(self):
        with _resolves_to("10.0.0.5"), pytest.raises(RecipeImportFetchError):
            RecipeImportService._validate_url("https://127.0.0.1.nip.io/recipe")

    def test_any_private_answer_is_rejected(self):
        with _resolves_to("93.184.216.34", "192.168.1.4"), pytest.raises(RecipeImportFetchError):
            RecipeImportService._validate_url("https://example.com/recipe")

    def test_public_site_is_allowed(self):
        with _resolves_to("93.184.216.34"):
            assert (
                RecipeImportService._validate_url("example.com/recipe")
                == "https://example.com/recipe"
            )

    def test_unresolvable_host_is_a_friendly_error(self):
        with patch(
            "app.services.ai.recipe_import.service.socket.getaddrinfo",
            side_effect=socket.gaierror("nope"),
        ), pytest.raises(RecipeImportFetchError):
            RecipeImportService._validate_url("https://no-such-host.example/")


class TestRecipeImportConnectionPinning:
    """The fetch re-resolves at connect time and dials only checked public IPs."""

    @pytest.mark.anyio
    async def test_rebinding_to_private_ip_is_refused_at_connect(self):
        """A name that passed validation but now resolves privately never connects."""
        inner_connect = AsyncMock()
        with _resolves_to("127.0.0.1"), patch(
            "httpcore.AnyIOBackend.connect_tcp", inner_connect
        ), pytest.raises(RecipeImportFetchError):
            await RecipeImportService._fetch_html("https://rebind.example/recipe")
        inner_connect.assert_not_called()

    @pytest.mark.anyio
    async def test_connects_to_the_checked_address(self):
        inner_connect = AsyncMock(side_effect=httpcore.ConnectError("refused"))
        with _resolves_to("93.184.216.34"), patch(
            "httpcore.AnyIOBackend.connect_tcp", inner_connect
        ), pytest.raises(RecipeImportFetchError, match="Could not reach"):
            await RecipeImportService._fetch_html("https://example.com/recipe")
        assert inner_connect.await_args.args[0] == "93.184.216.34"
        assert inner_connect.await_args.args[1] == 443

    @pytest.mark.anyio
    async def test_image_download_is_pinned_too(self):
        inner_connect = AsyncMock()
        with _resolves_to("10.0.0.8"), patch(
            "app.services.ai.recipe_import.service.RecipeImportService._validate_url",
            side_effect=lambda url: url,
        ), patch("httpcore.AnyIOBackend.connect_tcp", inner_connect):
            result = await RecipeImportService._download_image(
                "https://cdn.example/photo.jpg", "https://example.com/recipe"
            )
        assert result is None
        inner_connect.assert_not_called()


@pytest.fixture()
def admin_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'admin.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    admin = User(clerk_id="c_admin", email="a@example.com", is_admin=True)
    session.add(admin)
    session.commit()
    yield session, admin
    session.close()
    engine.dispose()


class TestAdminQueryConsole:
    @pytest.mark.parametrize(
        "query",
        [
            "SELECT 1; DELETE FROM users",
            "SELECT * INTO backup_users FROM users",
            "SELECT pg_sleep(60)",
            "SELECT pg_terminate_backend(123)",
            "PRAGMA writable_schema = 1",
            "EXPLAIN ANALYZE DELETE FROM users",
            "COMMIT",
        ],
    )
    def test_non_reads_are_refused(self, admin_session, query):
        session, admin = admin_session
        with pytest.raises(AdminQueryForbiddenError):
            AdminService(session, admin.id).execute_query(query)

    def test_select_still_works_and_leaves_session_writable(self, admin_session):
        session, admin = admin_session
        result = AdminService(session, admin.id).execute_query("SELECT email FROM users")
        assert result.rows == [["a@example.com"]]
        # query_only was switched back off
        session.add(User(clerk_id="c2", email="b@example.com"))
        session.commit()


class TestStripeWebhookTrust:
    def _service(self):
        service = StripeWebhookService(MagicMock())
        service.repo = MagicMock()
        return service

    def test_late_invoice_paid_does_not_revive_canceled_subscription(self):
        service = self._service()
        user = User(id=3, subscription_status="canceled", subscription_tier="free")
        service.repo.get_by_stripe_customer_id.return_value = user
        service.handle_event({"type": "invoice.paid", "data": {"object": {"customer": "cus_x"}}})
        service.repo.update_subscription.assert_not_called()

    def test_reference_id_for_someone_elses_customer_is_not_trusted(self):
        service = self._service()
        victim = User(id=1, stripe_customer_id="cus_victim")
        payer = User(id=2, stripe_customer_id="cus_payer")
        service.repo.get_by_id.return_value = victim
        service.repo.get_by_stripe_customer_id.return_value = payer
        service.handle_event(
            {
                "type": "checkout.session.completed",
                "data": {"object": {"customer": "cus_payer", "client_reference_id": "1", "mode": "subscription"}},
            }
        )
        assert service.repo.update_subscription.call_args.args[0] is payer

    def test_one_off_payment_checkout_does_not_grant_pro(self):
        service = self._service()
        service.handle_event(
            {
                "type": "checkout.session.completed",
                "data": {"object": {"customer": "cus_1", "client_reference_id": "1", "mode": "payment"}},
            }
        )
        service.repo.update_subscription.assert_not_called()
