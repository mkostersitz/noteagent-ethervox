//
//  AboutView.swift
//  NoteAgent macOS shell
//
//  Custom About window that replaces the default NSApplication About panel.
//  Shows version info and "Powered by EtherVox.ai" branding.
//

import SwiftUI

struct AboutView: View {
    private var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—"
    }
    private var buildNumber: String {
        Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "—"
    }

    var body: some View {
        VStack(spacing: 0) {
            // ── App icon + name ──────────────────────────────────────────
            VStack(spacing: 12) {
                if let icon = NSApp.applicationIconImage {
                    Image(nsImage: icon)
                        .resizable()
                        .frame(width: 80, height: 80)
                }

                Text("NoteAgent")
                    .font(.title.bold())

                Text("Version \(appVersion) (\(buildNumber))")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            .padding(.top, 28)
            .padding(.bottom, 20)

            Divider()

            // ── Description ──────────────────────────────────────────────
            Text("Local-first audio recording, transcription,\nand AI summarization for macOS.")
                .font(.callout)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.vertical, 16)
                .padding(.horizontal, 24)

            Divider()

            // ── EtherVox branding ────────────────────────────────────────
            VStack(spacing: 6) {
                Text("Powered by")
                    .font(.caption)
                    .foregroundStyle(.tertiary)

                Link(destination: URL(string: "https://ethervox.ai")!) {
                    HStack(spacing: 6) {
                        Image(systemName: "waveform")
                            .font(.system(size: 14, weight: .semibold))
                        Text("EtherVox.ai")
                            .font(.system(size: 14, weight: .semibold))
                    }
                    .foregroundStyle(.blue)
                }
            }
            .padding(.vertical, 16)

            Divider()

            // ── Copyright ────────────────────────────────────────────────
            Text("© 2025 NoteAgent contributors")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .padding(.vertical, 12)
        }
        .frame(width: 320)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// Thin NSWindowController wrapper so we can present this as a floating panel
// from anywhere in the app via AppDelegate / CommandGroup.
final class AboutWindowController: NSWindowController, NSWindowDelegate {
    static let shared = AboutWindowController()

    private init() {
        let view = AboutView()
        let hosting = NSHostingView(rootView: view)
        hosting.setFrameSize(hosting.fittingSize)

        let window = NSWindow(
            contentRect: NSRect(origin: .zero, size: hosting.fittingSize),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.title = "About NoteAgent"
        window.contentView = hosting
        window.isReleasedWhenClosed = false
        window.center()
        super.init(window: window)
        window.delegate = self
    }

    required init?(coder: NSCoder) { fatalError() }

    func show() {
        window?.center()
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}

#Preview {
    AboutView()
        .frame(width: 320)
}
