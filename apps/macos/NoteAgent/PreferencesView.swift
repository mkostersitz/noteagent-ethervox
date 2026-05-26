//
//  PreferencesView.swift
//  NoteAgent macOS shell
//
//  Preferences window (⌘,) — General settings covering the three most common
//  user-facing knobs:
//
//    1. Recordings folder  — stored in UserDefaults (Swift side); changes take
//                            effect on next launch since NOTEAGENT_STORAGE_DIR
//                            is passed to the Python server at startup.
//    2. Default audio device — read/written via the running server's /api/config
//                              endpoint so it applies immediately.
//    3. Transcription model  — read/written via /api/config. The new model is
//                              used on the next recording; no restart needed.
//

import SwiftUI

// MARK: - Model fetched from /api/config

private struct ServerConfig: Codable {
    var default_device: String
    var whisper_model: String
    var max_recording_duration: Double?  // seconds; nil = unlimited
}

// MARK: - Preference Tabs

enum PrefTab: String, CaseIterable, Identifiable {
    case general = "General"
    case audio   = "Audio"
    case transcription = "Transcription"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .general:       "gearshape"
        case .audio:         "mic"
        case .transcription: "waveform.and.magnifyingglass"
        }
    }
}

// MARK: - Top-level view

struct PreferencesView: View {
    @State private var selectedTab: PrefTab = .general

    var body: some View {
        TabView(selection: $selectedTab) {
            ForEach(PrefTab.allCases) { tab in
                tabContent(for: tab)
                    .tabItem {
                        Label(tab.rawValue, systemImage: tab.icon)
                    }
                    .tag(tab)
            }
        }
        .frame(width: 480, height: 360)
        .padding()
    }

    @ViewBuilder
    private func tabContent(for tab: PrefTab) -> some View {
        switch tab {
        case .general:       GeneralPrefsView()
        case .audio:         AudioPrefsView()
        case .transcription: TranscriptionPrefsView()
        }
    }
}

// MARK: - General tab

private struct GeneralPrefsView: View {
    @AppStorage(StoragePicker.defaultsKey) private var storagePath: String = ""

    // Duration options: tag 0 = unlimited, otherwise seconds
    private let durationOptions: [(label: String, seconds: Double)] = [
        ("No limit",  0),
        ("5 minutes",  5 * 60),
        ("10 minutes", 10 * 60),
        ("15 minutes", 15 * 60),
        ("30 minutes", 30 * 60),
        ("1 hour",     60 * 60),
        ("90 minutes", 90 * 60),
        ("2 hours",   120 * 60),
    ]

    @State private var selectedDuration: Double = 0   // 0 = unlimited
    @State private var durationSaveStatus: SaveStatus = .idle
    @State private var durationLoaded = false

    private enum SaveStatus { case idle, saved, failed }

    private var displayPath: String {
        storagePath.isEmpty ? "Not chosen yet" : storagePath
    }

    var body: some View {
        Form {
            // ── Recordings folder ────────────────────────────────────────
            Section {
                LabeledContent("Recordings folder") {
                    VStack(alignment: .trailing, spacing: 4) {
                        Text(URL(fileURLWithPath: displayPath).lastPathComponent.isEmpty
                             ? displayPath
                             : URL(fileURLWithPath: displayPath).lastPathComponent)
                            .foregroundStyle(storagePath.isEmpty ? .secondary : .primary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                        Text(storagePath.isEmpty ? "" : storagePath)
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                            .lineLimit(1)
                            .truncationMode(.middle)

                        Button("Change…") {
                            if let url = StoragePicker.runPicker() {
                                storagePath = url.path
                            }
                        }
                        .controlSize(.small)
                    }
                }
                .help("Where NoteAgent saves your recordings, transcripts, and exports. Takes effect on next launch.")
            } footer: {
                Text("Changes to the recordings folder take effect the next time NoteAgent starts.")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            // ── Default recording length ─────────────────────────────────
            Section {
                Picker("Max recording length", selection: $selectedDuration) {
                    ForEach(durationOptions, id: \.seconds) { opt in
                        Text(opt.label).tag(opt.seconds)
                    }
                }
                .onChange(of: selectedDuration) { _ in
                    guard durationLoaded else { return }
                    saveDuration()
                }
            } footer: {
                switch durationSaveStatus {
                case .idle:
                    Text("Recordings stop automatically after this time. \"No limit\" lets you stop manually.")
                        .font(.caption).foregroundStyle(.tertiary)
                case .saved:
                    Label("Saved", systemImage: "checkmark.circle.fill")
                        .font(.caption).foregroundStyle(.green)
                case .failed:
                    Label("Could not save — server may not be running",
                          systemImage: "exclamationmark.circle.fill")
                        .font(.caption).foregroundStyle(.orange)
                }
            }
        }
        .formStyle(.grouped)
        .task { await loadDuration() }
    }

    private func loadDuration() async {
        do {
            let (data, _) = try await URLSession.shared.data(
                from: URL(string: "http://127.0.0.1:8765/api/config")!)
            let cfg = try JSONDecoder().decode(ServerConfig.self, from: data)
            selectedDuration = cfg.max_recording_duration ?? 0
        } catch {
            // Server not running — leave "No limit" default
        }
        durationLoaded = true
    }

    private func saveDuration() {
        Task {
            do {
                var req = URLRequest(url: URL(string: "http://127.0.0.1:8765/api/config")!)
                req.httpMethod = "PUT"
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                // Send null (unlimited) when 0 is selected, otherwise the seconds value
                let body: [String: Double?] = ["max_recording_duration": selectedDuration > 0 ? selectedDuration : nil]
                req.httpBody = try JSONEncoder().encode(body)
                let (_, resp) = try await URLSession.shared.data(for: req)
                let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
                durationSaveStatus = (200..<300).contains(code) ? .saved : .failed
            } catch {
                durationSaveStatus = .failed
            }
            try? await Task.sleep(nanoseconds: 2_500_000_000)
            durationSaveStatus = .idle
        }
    }
}

// MARK: - Audio tab

private struct AudioPrefsView: View {
    @State private var devices: [String] = []
    @State private var selectedDevice: String = ""
    @State private var isSaving = false
    @State private var loadError: String?
    @State private var saveStatus: SaveStatus = .idle

    private enum SaveStatus { case idle, saved, failed }

    var body: some View {
        Form {
            Section {
                if let err = loadError {
                    LabeledContent("Status") {
                        Text(err)
                            .foregroundStyle(.secondary)
                            .font(.callout)
                    }
                } else {
                    Picker("Default device", selection: $selectedDevice) {
                        if devices.isEmpty {
                            Text("Loading…").tag("")
                        } else {
                            ForEach(devices, id: \.self) { device in
                                Text(device).tag(device)
                            }
                        }
                    }
                    .disabled(devices.isEmpty || isSaving)
                    .onChange(of: selectedDevice) { _ in saveDevicePreference() }
                }
            } footer: {
                switch saveStatus {
                case .idle:   EmptyView()
                case .saved:  statusLabel("Saved", color: .green, icon: "checkmark.circle.fill")
                case .failed: statusLabel("Could not save — server may not be running", color: .orange, icon: "exclamationmark.circle.fill")
                }
            }
        }
        .formStyle(.grouped)
        .task { await loadAudioSettings() }
    }

    @ViewBuilder
    private func statusLabel(_ text: String, color: Color, icon: String) -> some View {
        Label(text, systemImage: icon)
            .font(.caption)
            .foregroundStyle(color)
    }

    private func loadAudioSettings() async {
        loadError = nil
        do {
            // Fetch device list
            let (devData, _) = try await URLSession.shared.data(from: URL(string: "http://127.0.0.1:8765/api/devices")!)
            let devResp = try JSONDecoder().decode([String: [String]].self, from: devData)
            devices = devResp["devices"] ?? []

            // Fetch current config to pre-select the saved device
            let (cfgData, _) = try await URLSession.shared.data(from: URL(string: "http://127.0.0.1:8765/api/config")!)
            let cfg = try JSONDecoder().decode(ServerConfig.self, from: cfgData)
            if selectedDevice.isEmpty { selectedDevice = cfg.default_device }
        } catch {
            loadError = "Audio devices unavailable. Start NoteAgent first."
        }
    }

    private func saveDevicePreference() {
        guard !selectedDevice.isEmpty else { return }
        isSaving = true
        Task {
            defer { isSaving = false }
            do {
                var req = URLRequest(url: URL(string: "http://127.0.0.1:8765/api/config")!)
                req.httpMethod = "PUT"
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                req.httpBody = try JSONEncoder().encode(["default_device": selectedDevice])
                let (_, resp) = try await URLSession.shared.data(for: req)
                let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
                saveStatus = (200..<300).contains(code) ? .saved : .failed
            } catch {
                saveStatus = .failed
            }
            try? await Task.sleep(nanoseconds: 2_500_000_000)
            saveStatus = .idle
        }
    }
}

// MARK: - Transcription tab

private struct TranscriptionPrefsView: View {
    private struct ModelOption: Identifiable {
        let id: String
        let label: String
        let note: String
    }

    private let models: [ModelOption] = [
        ModelOption(id: "tiny.en",   label: "Tiny (English)",   note: "Fastest — good for short notes"),
        ModelOption(id: "base.en",   label: "Base (English)",   note: "Balanced speed and accuracy (default)"),
        ModelOption(id: "small.en",  label: "Small (English)",  note: "Better accuracy, ~2× slower"),
        ModelOption(id: "medium.en", label: "Medium (English)", note: "High accuracy, ~5× slower"),
    ]

    @State private var selectedModel: String = "base.en"
    @State private var isSaving = false
    @State private var saveStatus: SaveStatus = .idle

    private enum SaveStatus { case idle, saved, failed }

    var body: some View {
        Form {
            Section {
                Picker("Whisper model", selection: $selectedModel) {
                    ForEach(models) { m in
                        VStack(alignment: .leading) {
                            Text(m.label)
                        }
                        .tag(m.id)
                    }
                }
                .disabled(isSaving)
                .onChange(of: selectedModel) { _ in saveModelPreference() }

                if let m = models.first(where: { $0.id == selectedModel }) {
                    Text(m.note)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            } footer: {
                switch saveStatus {
                case .idle:   Text("The new model will be used on your next recording.")
                                  .font(.caption).foregroundStyle(.tertiary)
                case .saved:  Label("Saved", systemImage: "checkmark.circle.fill")
                                  .font(.caption).foregroundStyle(.green)
                case .failed: Label("Could not save — server may not be running",
                                    systemImage: "exclamationmark.circle.fill")
                                  .font(.caption).foregroundStyle(.orange)
                }
            }
        }
        .formStyle(.grouped)
        .task { await loadTranscriptionSettings() }
    }

    private func loadTranscriptionSettings() async {
        do {
            let (data, _) = try await URLSession.shared.data(from: URL(string: "http://127.0.0.1:8765/api/config")!)
            let cfg = try JSONDecoder().decode(ServerConfig.self, from: data)
            selectedModel = cfg.whisper_model
        } catch {
            // Server not running — leave default; user can still browse options
        }
    }

    private func saveModelPreference() {
        isSaving = true
        Task {
            defer { isSaving = false }
            do {
                var req = URLRequest(url: URL(string: "http://127.0.0.1:8765/api/config")!)
                req.httpMethod = "PUT"
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                req.httpBody = try JSONEncoder().encode(["whisper_model": selectedModel])
                let (_, resp) = try await URLSession.shared.data(for: req)
                let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
                saveStatus = (200..<300).contains(code) ? .saved : .failed
            } catch {
                saveStatus = .failed
            }
            try? await Task.sleep(nanoseconds: 2_500_000_000)
            saveStatus = .idle
        }
    }
}

#Preview {
    PreferencesView()
}
