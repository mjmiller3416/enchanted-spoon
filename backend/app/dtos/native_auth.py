"""Response for the native-shell sign-in ticket exchange."""

from pydantic import BaseModel, Field


class NativeTicketResponseDTO(BaseModel):
    """A one-minute Clerk sign-in token for the WebView's cookie session.

    This is the only field returned. The native session JWT and the Clerk
    Backend API payload stay on the server.
    """

    ticket: str = Field(..., min_length=1, max_length=4000)
