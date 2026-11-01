import UIKit
import UniformTypeIdentifiers

/// Share-sheet target. TikTok, Instagram, and other apps hand over a URL or
/// text; this opens Enchanted Spoon at `enchantedspoon://import?url=`.
@objc(ShareViewController)
class ShareViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        handleShare()
    }

    private func handleShare() {
        guard let item = extensionContext?.inputItems.first as? NSExtensionItem,
              let providers = item.attachments else {
            finish()
            return
        }

        let urlType = UTType.url.identifier
        let textType = UTType.plainText.identifier
        if let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(urlType) }) {
            provider.loadItem(forTypeIdentifier: urlType, options: nil) { data, _ in
                let raw = (data as? URL)?.absoluteString ?? ""
                self.openApp(with: raw)
            }
            return
        }
        if let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(textType) }) {
            provider.loadItem(forTypeIdentifier: textType, options: nil) { data, _ in
                self.openApp(with: data as? String ?? "")
            }
            return
        }
        finish()
    }

    private func openApp(with text: String) {
        let encoded = text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        guard let url = URL(string: "enchantedspoon://import?url=\(encoded)") else {
            finish()
            return
        }
        DispatchQueue.main.async {
            self.open(url)
            self.finish()
        }
    }

    /// Share extensions cannot call UIApplication.shared.open. Walk the
    /// responder chain, which is the supported way to hand a custom-scheme
    /// URL back to the host app.
    private func open(_ url: URL) {
        var responder: UIResponder? = self
        let selector = sel_registerName("openURL:")
        while let current = responder {
            if current.responds(to: selector) {
                current.perform(selector, with: url)
                return
            }
            responder = current.next
        }
    }

    private func finish() {
        extensionContext?.completeRequest(returningItems: [], completionHandler: nil)
    }
}
