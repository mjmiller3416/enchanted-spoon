import { DEFAULT_SETTINGS, deepMergeSettings, type AppSettings, type SettingsPatch } from "./settings";

function mergePatch(first: SettingsPatch, second: SettingsPatch): SettingsPatch {
  const result = { ...first };
  for (const key of Object.keys(second) as (keyof AppSettings)[]) {
    Object.assign(result, { [key]: { ...first[key], ...second[key] } });
  }
  return result;
}

type Snapshot = { settings: AppSettings; isLoaded: boolean; isSyncing: boolean; error: string | null };
type Transport = { get: () => Promise<Record<string, unknown>>; update: (patch: SettingsPatch) => Promise<Record<string, unknown>> };

/** One owner per account. Writes contain only edited fields and are serialized.
 * Pending edits are saved locally immediately, so closing the tab before the
 * debounce fires does not silently lose them. They resume on the next load. */
export class SettingsStore {
  private snapshot: Snapshot = { settings: DEFAULT_SETTINGS, isLoaded: false, isSyncing: false, error: null };
  private listeners = new Set<() => void>();
  private pending: SettingsPatch = {};
  private inFlight: SettingsPatch = {};
  private timer?: ReturnType<typeof setTimeout>;
  private saving = false;
  private active = true;
  private loadPromise?: Promise<void>;

  constructor(private key: string, private transport: Transport) {}
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  getSnapshot = () => this.snapshot;
  private emit(patch: Partial<Snapshot>) {
    this.snapshot = { ...this.snapshot, ...patch };
    this.listeners.forEach(listener => listener());
  }
  private storePending() {
    try { localStorage.setItem(`${this.key}:pending`, JSON.stringify(mergePatch(this.inFlight, this.pending))); } catch { /* Server save remains available. */ }
  }
  private storeSettings() {
    try {
      localStorage.setItem(this.key, JSON.stringify(this.snapshot.settings));
      localStorage.setItem("enchanted-spoon-theme", JSON.stringify(this.snapshot.settings.appearance.theme));
    } catch { /* Server save remains available. */ }
  }
  start = () => {
    this.active = true;
    this.loadPromise ??= this.load();
    return this.loadPromise;
  };
  private async load() {
    try {
      const cached = localStorage.getItem(this.key);
      if (cached) this.emit({ settings: deepMergeSettings(DEFAULT_SETTINGS, JSON.parse(cached)) });
      else {
        const theme = JSON.parse(localStorage.getItem("enchanted-spoon-theme") ?? "null");
        if (theme === "light" || theme === "dark" || theme === "system") this.emit({ settings: deepMergeSettings(DEFAULT_SETTINGS, { appearance: { theme } }) });
      }
      const pending = localStorage.getItem(`${this.key}:pending`);
      if (pending) this.pending = mergePatch(JSON.parse(pending), this.pending);
    } catch { /* Ignore invalid local data; fetch the authoritative settings. */ }
    try {
      const remote = await this.transport.get();
      this.emit({ settings: deepMergeSettings(deepMergeSettings(this.snapshot.settings, remote), this.pending), error: null });
    } catch {
      this.emit({ settings: deepMergeSettings(this.snapshot.settings, this.pending), error: "Couldn't load settings from the server. Local preferences are shown." });
    }
    this.emit({ isLoaded: true });
    if (this.active) {
      this.storeSettings();
      if (Object.keys(this.pending).length) void this.flush();
    }
  }
  update = (patch: SettingsPatch) => {
    this.pending = mergePatch(this.pending, patch);
    this.emit({ settings: deepMergeSettings(this.snapshot.settings, patch), isSyncing: true, error: null });
    this.storeSettings();
    this.storePending();
    clearTimeout(this.timer);
    this.timer = setTimeout(() => { void this.flush(); }, 500);
  };
  flush = async () => {
    if (this.saving || !this.active || !this.snapshot.isLoaded) return;
    clearTimeout(this.timer);
    this.saving = true;
    try {
      while (this.active && Object.keys(this.pending).length) {
        const batch = this.pending;
        this.inFlight = batch;
        this.pending = {};
        // Keep the in-flight batch in storage until it is acknowledged.
        this.emit({ isSyncing: true, error: null });
        try {
          const remote = await this.transport.update(batch);
          if (!this.active) return;
          this.inFlight = {};
          this.emit({ settings: deepMergeSettings(deepMergeSettings(this.snapshot.settings, remote), this.pending) });
          this.storeSettings();
          this.storePending();
        } catch {
          this.pending = mergePatch(batch, this.pending);
          this.inFlight = {};
          this.storePending();
          this.emit({ error: "Changes are kept on this device but haven't synced. Retry saving." });
          break;
        }
      }
    } finally {
      this.saving = false;
      this.emit({ isSyncing: false });
    }
  };
  refresh = async () => {
    if (!this.snapshot.isLoaded) return this.start();
    if (Object.keys(this.pending).length || this.saving) return this.flush();
    try {
      const remote = await this.transport.get();
      if (!this.active) return;
      this.emit({ settings: deepMergeSettings(deepMergeSettings(this.snapshot.settings, remote), mergePatch(this.inFlight, this.pending)), error: null });
      this.storeSettings();
    } catch { this.emit({ error: "Couldn't refresh settings. Please try again." }); }
  };
  dispose = () => { this.active = false; clearTimeout(this.timer); };
}
