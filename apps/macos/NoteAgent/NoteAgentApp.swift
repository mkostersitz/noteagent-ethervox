//
//  NoteAgentApp.swift
//  NoteAgent macOS shell
//
//  SwiftUI entry point. Owns the lifecycle of the embedded Python server and
//  the WKWebView window that consumes its API.
//

import SwiftUI

@main
struct NoteAgentApp: App {
    // Single source of truth for the embedded server. The view subscribes to
    // its `@Published` state so the WKWebView can render a loading indicator
    // until the server is ready.
    @StateObject private var server = PythonServer()

    var body: some Scene {
        // ── Main window ──────────────────────────────────────────────────
        WindowGroup("NoteAgent") {
            ContentView()
                .environmentObject(server)
                .frame(minWidth: 900, minHeight: 600)
                .onAppear { server.start() }
                .onDisappear { server.stop() }
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .commands {
            // ── File menu ────────────────────────────────────────────────
            CommandGroup(replacing: .newItem) {} // Hide File → New

            // ── App menu extras ──────────────────────────────────────────
            CommandGroup(replacing: .appInfo) {
                Button("About NoteAgent") {
                    AboutWindowController.shared.show()
                }
            }

            CommandGroup(after: .appInfo) {
                Button("Open NoteAgent in Browser") {
                    if let url = server.url {
                        NSWorkspace.shared.open(url)
                    }
                }
                .keyboardShortcut("b", modifiers: [.command, .shift])
            }

            // ── Help menu ────────────────────────────────────────────────
            CommandGroup(replacing: .help) {
                Button("NoteAgent Help") {
                    HelpWindowController.shared.show()
                }
                .keyboardShortcut("?", modifiers: .command)

                Divider()

                Button("Keyboard Shortcuts…") {
                    HelpWindowController.shared.show()
                }

                Divider()

                Link("Learn More About EtherVox.ai",
                     destination: URL(string: "https://ethervox.ai")!)

                Link("Open on GitHub",
                     destination: URL(string: "https://github.com/mkostersitz/noteagent-ethervox")!)
            }
        }

        // ── Preferences window (⌘,) ──────────────────────────────────────
        Settings {
            PreferencesView()
        }
    }
}
