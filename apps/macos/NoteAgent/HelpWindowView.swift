//
//  HelpWindowView.swift
//  NoteAgent macOS shell
//
//  In-app help panel accessible from Help → NoteAgent Help (⌘?).
//  Covers the main workflows, keyboard shortcuts, and links out to
//  the EtherVox.ai website and the GitHub repo for deeper docs.
//

import SwiftUI

// MARK: - Data model

private struct HelpSection: Identifiable {
    let id = UUID()
    let title: String
    let icon: String
    let items: [HelpItem]
}

private struct HelpItem: Identifiable {
    let id = UUID()
    let title: String
    let body: String
    let shortcut: String?

    init(_ title: String, _ body: String, shortcut: String? = nil) {
        self.title = title
        self.body = body
        self.shortcut = shortcut
    }
}

private let helpContent: [HelpSection] = [
    HelpSection(
        title: "Getting Started",
        icon: "play.circle",
        items: [
            HelpItem(
                "Record a note",
                "Click the microphone button in the toolbar (or press ⌃R) to start recording. Click again to stop. NoteAgent transcribes and optionally summarises the audio automatically.",
                shortcut: "⌃R"
            ),
            HelpItem(
                "Meeting mode",
                "Enable Meeting Mode to capture two audio streams at once — your microphone and a virtual system audio device (e.g. BlackHole 2ch). Ideal for recording calls."
            ),
            HelpItem(
                "Import audio",
                "Drag an existing .wav, .m4a, or .mp3 file into the app to transcribe it without recording."
            ),
        ]
    ),
    HelpSection(
        title: "Recordings & Sessions",
        icon: "waveform.path",
        items: [
            HelpItem(
                "Browse recordings",
                "All sessions are listed in the sidebar. Click a session to view its transcript, audio waveform, and AI summary."
            ),
            HelpItem(
                "Export a session",
                "Open a session and choose File → Export to save the transcript as plain text, Markdown, PDF, or WebVTT subtitle file."
            ),
            HelpItem(
                "Delete a session",
                "Right-click a session in the sidebar and choose Delete, or open the session and press ⌫."
            ),
        ]
    ),
    HelpSection(
        title: "Transcription & AI",
        icon: "brain",
        items: [
            HelpItem(
                "Changing the model",
                "Go to NoteAgent → Preferences → Transcription to switch between Whisper model sizes. Larger models are more accurate but slower. Changes take effect on the next recording."
            ),
            HelpItem(
                "Summaries",
                "After a recording finishes NoteAgent automatically generates a summary. You can also re-summarise any session from its detail view."
            ),
            HelpItem(
                "Local processing only",
                "All audio, transcription, and summarisation runs on-device by default. Nothing is sent to the cloud unless you configure an external LLM endpoint in Preferences."
            ),
        ]
    ),
    HelpSection(
        title: "Keyboard Shortcuts",
        icon: "keyboard",
        items: [
            HelpItem("Open in browser", "Open the NoteAgent web UI in your default browser.", shortcut: "⌘⇧B"),
            HelpItem("Preferences", "Open the Preferences window.", shortcut: "⌘,"),
            HelpItem("Start / stop recording", "Toggle recording from anywhere in the app.", shortcut: "⌃R"),
        ]
    ),
    HelpSection(
        title: "Troubleshooting",
        icon: "wrench.and.screwdriver",
        items: [
            HelpItem(
                "App stuck on \"Starting NoteAgent\"",
                "The embedded Python server is taking longer than 60 seconds. This can happen on first launch when models are loading. Quit the app, wait a moment, and reopen it. If the problem persists, check the Console app for errors from the \"ai.ethervox.noteagent\" subsystem."
            ),
            HelpItem(
                "No audio devices listed",
                "Check that the app has microphone permission in System Settings → Privacy & Security → Microphone. After granting permission, quit and reopen NoteAgent."
            ),
            HelpItem(
                "Transcription is inaccurate",
                "Switch to a larger Whisper model in Preferences \u{2192} Transcription. The \"small.en\" or \"medium.en\" models significantly improve accuracy at the cost of speed."
            ),
        ]
    ),
]

// MARK: - Views

struct HelpWindowView: View {
    @State private var selectedSection: UUID?

    var body: some View {
        NavigationSplitView {
            sidebarList
        } detail: {
            if let id = selectedSection,
               let section = helpContent.first(where: { $0.id == id }) {
                SectionDetailView(section: section)
            } else {
                WelcomeDetailView()
            }
        }
        .navigationTitle("NoteAgent Help")
        .frame(minWidth: 680, minHeight: 480)
    }

    private var sidebarList: some View {
        List(helpContent, selection: $selectedSection) { section in
            Label(section.title, systemImage: section.icon)
                .tag(section.id)
        }
        .listStyle(.sidebar)
        .frame(minWidth: 190)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Link(destination: URL(string: "https://ethervox.ai")!) {
                    Label("EtherVox.ai", systemImage: "arrow.up.right.square")
                }
                .help("Open EtherVox.ai website")
            }
        }
    }
}

private struct WelcomeDetailView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "waveform.and.magnifyingglass")
                .font(.system(size: 48))
                .foregroundStyle(.blue.gradient)
            Text("NoteAgent Help")
                .font(.title2.bold())
            Text("Select a topic from the sidebar to get started,\nor use ⌘F to search.")
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

private struct SectionDetailView: View {
    let section: HelpSection

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                // Header
                HStack(spacing: 12) {
                    Image(systemName: section.icon)
                        .font(.system(size: 22, weight: .semibold))
                        .foregroundStyle(.blue)
                    Text(section.title)
                        .font(.title2.bold())
                }
                .padding(.horizontal, 28)
                .padding(.top, 28)
                .padding(.bottom, 20)

                Divider()
                    .padding(.horizontal, 28)

                // Items
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(section.items) { item in
                        HelpItemRow(item: item)
                    }
                }
                .padding(.top, 8)
                .padding(.bottom, 28)
            }
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

private struct HelpItemRow: View {
    let item: HelpItem
    @State private var isExpanded = true

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Title row
            HStack {
                Text(item.title)
                    .font(.headline)
                Spacer()
                if let shortcut = item.shortcut {
                    Text(shortcut)
                        .font(.system(.caption, design: .monospaced))
                        .padding(.horizontal, 7)
                        .padding(.vertical, 3)
                        .background(Color(nsColor: .quaternaryLabelColor).opacity(0.5),
                                    in: RoundedRectangle(cornerRadius: 5))
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 28)
            .padding(.vertical, 12)

            // Body text
            Text(item.body)
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.horizontal, 28)
                .padding(.bottom, 14)

            Divider()
                .padding(.horizontal, 28)
        }
    }
}

// MARK: - Window controller

final class HelpWindowController: NSWindowController, NSWindowDelegate {
    static let shared = HelpWindowController()

    private init() {
        let view = HelpWindowView()
        let hosting = NSHostingView(rootView: view)

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 720, height: 520),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "NoteAgent Help"
        window.contentView = hosting
        window.isReleasedWhenClosed = false
        window.center()
        super.init(window: window)
        window.delegate = self
    }

    required init?(coder: NSCoder) { fatalError() }

    func show() {
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}

#Preview {
    HelpWindowView()
}
