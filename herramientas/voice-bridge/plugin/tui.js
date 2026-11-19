/**
 * voice-bridge TUI plugin (local, CLI-only).
 *
 * Ctrl+Alt+V toggles push-to-talk inside OpenCode:
 *   1st press -> record
 *   2nd press -> transcribe, copy to clipboard, paste into the composer
 *              and speak a short confirmation with the configured voice.
 *
 * No credentials are read or stored here; voicectl.py owns that.
 */

const VOICECTL =
  "/home/dev/Documentos/Debian_Hyprland_Look_And_Feel/herramientas/voice-bridge/voicectl.py";

let recording = false;
let busy = false;

function notify(api, message, variant = "info") {
  const toast = api?.ui?.toast;
  if (toast && typeof toast.show === "function") {
    toast.show({ message, variant, duration: 3000 });
  } else if (typeof toast === "function") {
    toast({ message, variant, duration: 3000 });
  } else if (api?.notification?.show) {
    api.notification.show({ message });
  }
}

function spawnText(command, args, options = {}) {
  return import("node:child_process").then(({ spawn }) =>
    new Promise((resolve, reject) => {
      const child = spawn(command, args, {
        stdio: ["ignore", "pipe", "pipe"],
        env: { ...process.env, ...(options.env || {}) },
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (chunk) => { stdout += chunk; });
      child.stderr.on("data", (chunk) => { stderr += chunk; });
      child.on("error", reject);
      child.on("close", (code) => {
        if (code === 0) resolve(stdout.trim());
        else reject(new Error(stderr.trim() || `${command} exited ${code}`));
      });
    })
  );
}

function voicectl(args) {
  // Keep delivery inside the TUI: no PTY typing from the Python side.
  return spawnText("python3", [VOICECTL, ...args], {
    env: { VOICE_DELIVER_BACKEND: "none" },
  });
}

function copyToClipboard(text) {
  return import("node:child_process").then(({ spawn }) =>
    new Promise((resolve, reject) => {
      const child = spawn("wl-copy", [], { stdio: ["pipe", "ignore", "pipe"] });
      let stderr = "";
      child.stderr.on("data", (chunk) => { stderr += chunk; });
      child.on("error", reject);
      child.on("close", (code) => {
        if (code === 0) resolve();
        else reject(new Error(stderr.trim() || `wl-copy exited ${code}`));
      });
      child.stdin.end(text);
    })
  );
}

async function pasteIntoComposer(api) {
  try {
    if (api?.keymap?.dispatchCommand) {
      await api.keymap.dispatchCommand("prompt.paste");
      return true;
    }
    if (api?.keymap?.dispatch) {
      await api.keymap.dispatch("prompt.paste");
      return true;
    }
    if (api?.command?.trigger) {
      api.command.trigger("prompt.paste");
      return true;
    }
  } catch {
    // Fall through to the clipboard-only instruction.
  }
  return false;
}

async function dictate(api) {
  if (busy) return;
  busy = true;
  try {
    if (!recording) {
      await voicectl(["start"]);
      recording = true;
      notify(api, "Grabando… pulsa Ctrl+Alt+V para terminar");
      return;
    }

    recording = false;
    notify(api, "Transcribiendo…");
    const raw = await voicectl(["stop"]);
    const result = JSON.parse(raw);
    const text = String(result.text || "").trim();
    if (!text) {
      notify(api, "Sin transcripción", "warning");
      return;
    }

    await copyToClipboard(text);
    const pasted = await pasteIntoComposer(api);
    notify(
      api,
      pasted ? `Dictado: ${text.slice(0, 80)}` : `Copiado, pega con Ctrl+V: ${text.slice(0, 60)}`,
      "success"
    );

    try {
      await voicectl(["speak", "Entendido"]);
    } catch {
      // Audio confirmation is best-effort; the transcript is already delivered.
    }
  } catch (error) {
    recording = false;
    notify(api, `voice-bridge: ${error.message || error}`, "error");
  } finally {
    busy = false;
  }
}

function register(api) {
  const run = () => dictate(api);

  // V2 keymap API.
  if (api?.keymap?.layer) {
    return api.keymap.layer(() => ({
      mode: "global",
      commands: [
        {
          id: "voice.dictate",
          title: "Voice: dictar",
          description: "Inicia o detiene el dictado y lo pega en el composer",
          group: "Voice",
          bind: "ctrl+alt+v",
          keybind: "ctrl+alt+v",
          palette: true,
          slash: { name: "voice-dictate" },
          run,
        },
      ],
      bindings: ["voice.dictate"],
    }));
  }

  // Keymap API shipped with OpenCode 1.19.x.
  if (api?.keymap?.registerLayer) {
    return api.keymap.registerLayer({
      commands: [
        {
          name: "voice.dictate",
          title: "Voice: dictar",
          description: "Inicia o detiene el dictado y lo pega en el composer",
          category: "Voice",
          bind: "ctrl+alt+v",
          keybind: "ctrl+alt+v",
          slash: { name: "voice-dictate" },
          onSelect: run,
        },
      ],
    });
  }

  // Legacy command API fallback.
  if (api?.command?.register) {
    return api.command.register(() => [
      {
        value: "voice.dictate",
        title: "Voice: dictar",
        description: "Inicia o detiene el dictado y lo pega en el composer",
        category: "Voice",
        keybind: "ctrl+alt+v",
        onSelect: run,
      },
    ]);
  }

  notify(api, "voice-bridge: no keymap API disponible", "warning");
}

export default {
  id: "voice-bridge-tui",
  tui: async (api) => {
    register(api);
  },
};
