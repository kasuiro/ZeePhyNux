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
import { appendFileSync, writeFileSync } from "node:fs"

const STATE_DIR = "/home/dev/.local/state/voice-bridge"
const LOAD_MARKER = `${STATE_DIR}/plugin-load.json`
const DEBUG_LOG = `${STATE_DIR}/plugin-debug.log`

function debug(message) {
  try {
    appendFileSync(DEBUG_LOG, `[${new Date().toISOString()}] ${message}\n`)
  } catch {
    // Diagnóstico best-effort.
  }
}

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
      new Promise((resolve) => {
        // wl-copy forks into the background to own the selection. The daemon
        // keeps inherited stdio open, so waiting for "close" hangs forever.
        // "exit" fires as soon as the direct child hands off the selection.
        const child = spawn("wl-copy", [], {
          stdio: ["pipe", "ignore", "ignore"],
        })
        let settled = false
        const done = () => {
          if (settled) return
          settled = true
          resolve()
        }
        child.on("error", done)
        child.on("exit", done)
        child.stdin.end(text)
        setTimeout(done, 1500)
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
  debug(`key press (busy=${busy}, recording=${recording})`)
  if (busy) {
    debug("ignored: busy")
    return
  }
  busy = true
  // Safety net: a hung child process must never lock the toggle permanently.
  const watchdog = setTimeout(() => {
    if (!busy) return
    debug("watchdog: busy timeout, reiniciando estado")
    busy = false
    recording = false
    notify(context, "voice-bridge: timeout, listo para reintentar", "warning")
  }, 120000)
  try {
    if (!recording) {
      const raw = await voicectl(["start"])
      debug(`start -> ${raw}`)
      recording = true
      notify(context, "Grabando… pulsa Ctrl+Alt+V para terminar")
      debug("toast grabando enviado")
      return
    }

    recording = false
    notify(context, "Transcribiendo…")
    const raw = await voicectl(["stop"])
    debug(`stop -> ${raw.slice(0, 200)}`)
    const result = JSON.parse(raw)
    const text = String(result.text || "").trim()
    if (!text) {
      notify(context, "Sin transcripción", "warning")
      debug("sin transcripcion")
      return
    }

    await copyToClipboard(text)
    debug("copiado al portapapeles")
    const pasted = await pasteIntoComposer(context)
    debug(`paste -> ${pasted}`)
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
    debug(`ERROR: ${error.message || error}`)
    notify(context, `voice-bridge: ${error.message || error}`, "error")
  } finally {
    clearTimeout(watchdog)
    busy = false
    debug("finally")
  }
}

export default Plugin.define({
  id: "voice-bridge-tui",
  setup(context) {
    debug("setup init")
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
