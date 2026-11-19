/**
 * voice-bridge TUI plugin (local, CLI-only, OpenCode V2).
 *
 * Ctrl+Alt+V toggles push-to-talk inside OpenCode:
 *   1st press -> record
 *   2nd press -> transcribe, copy to clipboard, paste into the composer
 *              and speak a short confirmation with the configured voice.
 *
 * No credentials are read or stored here; voicectl.py owns that.
 */

import { Plugin } from "@opencode/plugin/tui"
import { writeFileSync } from "node:fs"

const LOAD_MARKER =
  "/home/dev/.local/state/voice-bridge/plugin-load.json"

const VOICECTL =
  "/home/dev/Documentos/Debian_Hyprland_Look_And_Feel/herramientas/voice-bridge/voicectl.py"

let recording = false
let busy = false

function notify(context, message, variant = "info") {
  context.ui.toast?.show?.({ message, variant, duration: 3000 })
}

function spawnText(command, args, options = {}) {
  return import("node:child_process").then(
    ({ spawn }) =>
      new Promise((resolve, reject) => {
        const child = spawn(command, args, {
          stdio: ["ignore", "pipe", "pipe"],
          env: { ...process.env, ...(options.env || {}) },
        })
        let stdout = ""
        let stderr = ""
        child.stdout.on("data", (chunk) => {
          stdout += chunk
        })
        child.stderr.on("data", (chunk) => {
          stderr += chunk
        })
        child.on("error", reject)
        child.on("close", (code) => {
          if (code === 0) resolve(stdout.trim())
          else reject(new Error(stderr.trim() || `${command} exited ${code}`))
        })
      })
  )
}

function voicectl(args) {
  // Keep delivery inside the TUI: no PTY typing from the Python side.
  return spawnText("python3", [VOICECTL, ...args], {
    env: { VOICE_DELIVER_BACKEND: "none" },
  })
}

function copyToClipboard(text) {
  return import("node:child_process").then(
    ({ spawn }) =>
      new Promise((resolve, reject) => {
        const child = spawn("wl-copy", [], { stdio: ["pipe", "ignore", "pipe"] })
        let stderr = ""
        child.stderr.on("data", (chunk) => {
          stderr += chunk
        })
        child.on("error", reject)
        child.on("close", (code) => {
          if (code === 0) resolve()
          else reject(new Error(stderr.trim() || `wl-copy exited ${code}`))
        })
        child.stdin.end(text)
      })
  )
}

async function pasteIntoComposer(context) {
  try {
    if (context.keymap?.dispatch) {
      await context.keymap.dispatch("prompt.paste")
      return true
    }
    if (context.keymap?.dispatchCommand) {
      await context.keymap.dispatchCommand("prompt.paste")
      return true
    }
  } catch {
    // Fall through to the clipboard-only instruction.
  }
  return false
}

async function dictate(context) {
  if (busy) return
  busy = true
  try {
    if (!recording) {
      await voicectl(["start"])
      recording = true
      notify(context, "Grabando… pulsa Ctrl+Alt+V para terminar")
      return
    }

    recording = false
    notify(context, "Transcribiendo…")
    const raw = await voicectl(["stop"])
    const result = JSON.parse(raw)
    const text = String(result.text || "").trim()
    if (!text) {
      notify(context, "Sin transcripción", "warning")
      return
    }

    await copyToClipboard(text)
    const pasted = await pasteIntoComposer(context)
    notify(
      context,
      pasted
        ? `Dictado: ${text.slice(0, 80)}`
        : `Copiado, pega con Ctrl+V: ${text.slice(0, 60)}`,
      "success"
    )

    try {
      await voicectl(["speak", "Entendido"])
    } catch {
      // Audio confirmation is best-effort; the transcript is already delivered.
    }
  } catch (error) {
    recording = false
    notify(context, `voice-bridge: ${error.message || error}`, "error")
  } finally {
    busy = false
  }
}

export default Plugin.define({
  id: "voice-bridge-tui",
  setup(context) {
    try {
      writeFileSync(
        LOAD_MARKER,
        JSON.stringify({ loaded: true, at: new Date().toISOString() })
      )
    } catch {
      // Diagnóstico best-effort.
    }
    notify(context, "voice-bridge TUI listo · Ctrl+Alt+V", "success")

    context.keymap.layer(() => ({
      mode: "global",
      commands: [
        {
          id: "voice.dictate",
          title: "Voice: dictar",
          description: "Inicia o detiene el dictado y lo pega en el composer",
          group: "Voice",
          bind: "ctrl+alt+v",
          palette: true,
          slash: { name: "voice-dictate" },
          run: () => dictate(context),
        },
      ],
      bindings: ["voice.dictate"],
    }))
  },
})
