import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'

type RetrievedChunk = {
  doc_id: string
  title: string
  excerpt: string
  score: number
}

type DiagnosticEvent = {
  id: string
  received_at: string
  payload: {
    machine_id: string
    timestamp_iso?: string | null
    asset_class?: string | null
    thermal_c?: number | null
    thermal_baseline_c?: number | null
    acoustic_anomaly?: boolean
    acoustic_band_hz?: string | null
    rgb_summary?: string | null
    trigger_reason?: string | null
    notes?: string | null
    edge_hypothesis?: string | null
  }
  diagnosis_title: string
  diagnosis_body: string
  retrieved: RetrievedChunk[]
  work_order_stub: Record<string, unknown>
}

function mergeById(prev: DiagnosticEvent[], incoming: DiagnosticEvent): DiagnosticEvent[] {
  const rest = prev.filter((e) => e.id !== incoming.id)
  return [incoming, ...rest]
}

const demoPayloads = {
  driveShaft: {
    machine_id: 'conveyance-main-drive-1',
    thermal_c: 86,
    thermal_baseline_c: 48,
    acoustic_anomaly: true,
    acoustic_band_hz: '2000-4000',
    rgb_summary: 'Heat shimmer at main drive pillow block; belt tracking nominal.',
    trigger_reason: 'drive_shaft_thermal_and_bearing_acoustic',
  },
  mergeRotary: {
    machine_id: 'merge-table-rotary-2',
    thermal_c: 78,
    thermal_baseline_c: 44,
    acoustic_anomaly: true,
    acoustic_band_hz: '500-1200',
    rgb_summary: 'Star wheel chatter; guard clearance looks tight.',
    trigger_reason: 'rotary_unit_misalignment_trend',
  },
} as const

export default function App() {
  const [events, setEvents] = useState<DiagnosticEvent[]>([])
  const [health, setHealth] = useState<{ rag_chunks?: number } | null>(null)
  const [wsState, setWsState] = useState<'connecting' | 'open' | 'closed'>('closed')
  const [busy, setBusy] = useState(false)
  const [audioMachineId, setAudioMachineId] = useState('conveyance-main-drive-1')
  const [audioAssetClass, setAudioAssetClass] = useState('')
  const [audioError, setAudioError] = useState<string | null>(null)
  const [audioFile, setAudioFile] = useState<File | null>(null)

  const refresh = useCallback(async () => {
    const [h, ev] = await Promise.all([
      fetch('/api/health').then((r) => r.json()),
      fetch('/api/events').then((r) => r.json()),
    ])
    setHealth(h)
    setEvents(ev as DiagnosticEvent[])
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${window.location.host}/ws/events`
    setWsState('connecting')
    const ws = new WebSocket(url)
    ws.onopen = () => setWsState('open')
    ws.onclose = () => setWsState('closed')
    ws.onmessage = (msg) => {
      try {
        const ev = JSON.parse(msg.data as string) as DiagnosticEvent
        setEvents((prev) => mergeById(prev, ev))
      } catch {
        /* ignore */
      }
    }
    const ping = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, 25000)
    return () => {
      window.clearInterval(ping)
      ws.close()
    }
  }, [])

  const postDemo = async (body: object) => {
    setBusy(true)
    try {
      const r = await fetch('/api/demo/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (r.ok) {
        const ev = (await r.json()) as DiagnosticEvent
        setEvents((prev) => mergeById(prev, ev))
      }
    } finally {
      setBusy(false)
    }
  }

  const postAudioDiagnose = async (file: File | null) => {
    if (!file) return
    setBusy(true)
    setAudioError(null)
    try {
      const fd = new FormData()
      fd.append('machine_id', audioMachineId)
      fd.append('audio', file)
      const ac = audioAssetClass.trim()
      if (ac) fd.append('asset_class', ac)
      const r = await fetch('/api/audio/diagnose', { method: 'POST', body: fd })
      if (!r.ok) {
        let msg = 'Audio diagnosis request failed'
        try {
          const j = (await r.json()) as { detail?: unknown }
          if (typeof j.detail === 'string') msg = j.detail
        } catch {
          /* ignore */
        }
        setAudioError(msg)
        return
      }
      const ev = (await r.json()) as DiagnosticEvent
      setEvents((prev) => mergeById(prev, ev))
      setAudioFile(null)
    } finally {
      setBusy(false)
    }
  }

  const statusDot = useMemo(() => {
    const color =
      wsState === 'open' ? 'bg-emerald-400' : wsState === 'connecting' ? 'bg-amber-400' : 'bg-red-400'
    return color
  }, [wsState])

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_120%_80%_at_50%_-20%,#1e3a5f_0%,#09090b_55%)]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6">
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-amber-400/90">
              Factory Genius
            </p>
            <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Conveyance &amp; rotary maintenance
            </h1>
            <p className="mt-1 max-w-xl text-sm text-zinc-400">
              Multimodal maintenance copilot: live MQTT feed, machinery audio spectral hints, BM25 manual retrieval, and hints for{' '}
              <strong className="text-zinc-300">preventive</strong> vs <strong className="text-zinc-300">breakdown</strong>{' '}
              guidance (optional LLM). Upload WAV/FLAC for on-server STFT analysis—always validate on site.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-zinc-300">
              <span className={`h-2 w-2 rounded-full ${statusDot} animate-pulse`} aria-hidden />
              WebSocket: {wsState}
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-zinc-300">
              RAG chunks: {health?.rag_chunks ?? '—'}
            </span>
            <button
              type="button"
              onClick={() => void refresh()}
              className="rounded-full border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm font-medium text-amber-100 transition hover:bg-amber-500/20"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6">
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-xl shadow-black/40 backdrop-blur">
          <h2 className="font-display text-lg font-semibold text-white">
            Inject demo anomaly
          </h2>
          <p className="mt-1 text-sm text-zinc-400">
            Calls <code className="rounded bg-black/40 px-1.5 py-0.5 text-amber-200/90">POST /api/demo/ingest</code>{' '}
            — or run <code className="rounded bg-black/40 px-1.5 py-0.5">scripts/edge_simulator.py</code> (topic{' '}
            <code className="rounded bg-black/40 px-1.5 py-0.5">{'conveyance/{asset_id}/anomaly'}</code>) with Mosquitto.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => void postDemo(demoPayloads.driveShaft)}
              className="rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 px-5 py-2.5 text-sm font-semibold text-zinc-950 shadow-lg shadow-amber-900/30 disabled:opacity-50"
            >
              Main drive shaft scenario
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void postDemo(demoPayloads.mergeRotary)}
              className="rounded-xl border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10 disabled:opacity-50"
            >
              Merge rotary unit scenario
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-violet-500/20 bg-violet-950/[0.12] p-6 shadow-xl shadow-black/40 backdrop-blur">
          <h2 className="font-display text-lg font-semibold text-white">Diagnose from machinery audio</h2>
          <p className="mt-1 text-sm text-zinc-400">
            <code className="rounded bg-black/40 px-1.5 py-0.5 text-violet-200/90">POST /api/audio/diagnose</code> — upload a short
            WAV/FLAC clip; the server runs STFT band-energy analysis, then BM25 (+ optional LLM). Heuristic only—confirm with vibration,
            thermal, and site procedures.
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="block text-xs font-medium uppercase tracking-wide text-zinc-500">
              Machine ID
              <input
                type="text"
                value={audioMachineId}
                onChange={(e) => setAudioMachineId(e.target.value)}
                disabled={busy}
                className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none ring-violet-500/40 focus:ring-2"
              />
            </label>
            <label className="block text-xs font-medium uppercase tracking-wide text-zinc-500">
              Asset class (optional)
              <input
                type="text"
                value={audioAssetClass}
                onChange={(e) => setAudioAssetClass(e.target.value)}
                placeholder="e.g. conveyor, cnc, stamping_press"
                disabled={busy}
                className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none ring-violet-500/40 focus:ring-2"
              />
            </label>
          </div>
          <input
            type="file"
            accept=".wav,.flac,.ogg,audio/wav,audio/flac,audio/ogg"
            disabled={busy}
            onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
            className="mt-4 block w-full text-sm text-zinc-300 file:mr-4 file:rounded-lg file:border-0 file:bg-violet-500/25 file:px-4 file:py-2 file:text-sm file:font-medium file:text-violet-100 hover:file:bg-violet-500/35 disabled:opacity-50"
          />
          {audioFile && (
            <p className="mt-2 text-xs text-zinc-500">
              Selected: <span className="font-mono text-zinc-400">{audioFile.name}</span> (
              {(audioFile.size / 1024).toFixed(1)} KB)
            </p>
          )}
          {audioError && <p className="mt-2 text-sm text-red-300">{audioError}</p>}
          <button
            type="button"
            disabled={busy || !audioFile}
            onClick={() => void postAudioDiagnose(audioFile)}
            className="mt-4 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/30 disabled:opacity-50"
          >
            Run audio → RAG diagnosis
          </button>
        </section>

        <section>
          <h2 className="font-display mb-4 text-lg font-semibold text-white">
            Diagnostic feed
          </h2>
          {events.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] px-6 py-16 text-center text-zinc-500">
              No events yet. Start the API, then inject a demo, upload machinery audio, or publish over MQTT.
            </div>
          ) : (
            <ul className="space-y-6">
              {events.map((ev) => (
                <li
                  key={ev.id}
                  className="overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.06] to-transparent shadow-lg shadow-black/30"
                >
                  <div className="border-b border-white/10 bg-black/20 px-5 py-4 sm:flex sm:items-start sm:justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-wider text-amber-400/90">
                        {ev.payload.machine_id}
                      </p>
                      <h3 className="font-display text-xl font-semibold text-white">
                        {ev.diagnosis_title}
                      </h3>
                      <p className="mt-1 text-xs text-zinc-500">
                        {new Date(ev.received_at).toLocaleString()} · {ev.payload.trigger_reason ?? 'event'}
                      </p>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 sm:mt-0">
                      {ev.payload.thermal_c != null && (
                        <Metric label="Thermal" value={`${ev.payload.thermal_c}°C`} warn={(ev.payload.thermal_c ?? 0) > 80} />
                      )}
                      {ev.payload.acoustic_anomaly && (
                        <span className="rounded-lg bg-violet-500/20 px-2.5 py-1 text-xs font-medium text-violet-200">
                          Acoustic anomaly
                          {ev.payload.acoustic_band_hz ? ` · ${ev.payload.acoustic_band_hz}` : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="grid gap-6 p-5 lg:grid-cols-5">
                    <div className="space-y-3 lg:col-span-2">
                      <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Evidence</h4>
                      {ev.payload.rgb_summary && (
                        <p className="text-sm leading-relaxed text-zinc-300">{ev.payload.rgb_summary}</p>
                      )}
                      {ev.payload.edge_hypothesis && (
                        <p className="text-sm leading-relaxed text-violet-200/90">
                          <span className="font-semibold text-violet-300/90">Audio / edge hypothesis:</span>{' '}
                          {ev.payload.edge_hypothesis}
                        </p>
                      )}
                      {ev.payload.notes && (
                        <p className="text-xs leading-relaxed text-zinc-500">Signal notes: {ev.payload.notes}</p>
                      )}
                      <div className="rounded-xl border border-white/10 bg-black/30 p-4 text-xs text-zinc-400">
                        <p className="font-mono text-[11px] leading-relaxed break-all">
                          Work order stub: {JSON.stringify(ev.work_order_stub)}
                        </p>
                      </div>
                    </div>
                    <div className="lg:col-span-3">
                      <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Diagnosis</h4>
                      <div className="mt-2">
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => (
                              <p className="mb-2 text-sm leading-relaxed text-zinc-300">{children}</p>
                            ),
                            strong: ({ children }) => (
                              <strong className="font-semibold text-amber-100">{children}</strong>
                            ),
                            ul: ({ children }) => (
                              <ul className="mb-2 list-disc space-y-1 pl-5 text-sm text-zinc-300">{children}</ul>
                            ),
                            ol: ({ children }) => (
                              <ol className="mb-2 list-decimal space-y-1 pl-5 text-sm text-zinc-300">{children}</ol>
                            ),
                            li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                            h1: ({ children }) => (
                              <h4 className="mb-2 font-display text-base font-semibold text-white">
                                {children}
                              </h4>
                            ),
                            h2: ({ children }) => (
                              <h4 className="mb-2 font-display text-base font-semibold text-white">
                                {children}
                              </h4>
                            ),
                          }}
                        >
                          {ev.diagnosis_body}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                  <div className="border-t border-white/10 bg-black/25 px-5 py-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Retrieved manual chunks</h4>
                    <ul className="mt-3 space-y-2">
                      {ev.retrieved.map((r) => (
                        <li
                          key={`${ev.id}-${r.doc_id}-${r.title}`}
                          className="rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2 text-sm"
                        >
                          <span className="font-medium text-amber-100/90">{r.title}</span>
                          <span className="ml-2 text-xs text-zinc-500">({r.doc_id})</span>
                          <p className="mt-1 text-xs leading-relaxed text-zinc-400">{r.excerpt}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>

      <footer className="border-t border-white/10 py-8 text-center text-xs text-zinc-600">
        Prototype — not for production safety decisions. See docs/product/plan.md &amp; docs/architecture/overview.md.
      </footer>
    </div>
  )
}

function Metric({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <span
      className={`rounded-lg px-2.5 py-1 text-xs font-medium ${
        warn ? 'bg-red-500/20 text-red-200' : 'bg-emerald-500/15 text-emerald-200'
      }`}
    >
      {label}: {value}
    </span>
  )
}
