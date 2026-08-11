import { useEffect, useId, useRef, useState } from "react";
import "./Landing.css";

/* ---------------------------------------------------------------- shared */

function DataStat({ value, label, tone }) {
    return <div className={`ld-stat${tone ? ` ld-stat-${tone}` : ""}`}>
        <strong>{value}</strong>
        <span>{label}</span>
    </div>;
}

function SampleTag() {
    return <span className="ld-stamp ld-stamp-sample">Sample data</span>;
}

function Illustrative({ children }) {
    return <p className="ld-illustrative"><SampleTag />{" "}{children}</p>;
}

function useMyChannelLanding() {
    const [value, setValue] = useState(() => localStorage.getItem("yt-my-channel") || "");
    return [value, (v) => { setValue(v); if (v) localStorage.setItem("yt-my-channel", v); }];
}

/* A 16:9 mock video thumbnail + channel identity strip - the one recurring
   visual unit that makes this a video-intelligence product rather than a
   generic data tool. Reused across Discover, Analyse and Monitor. */
function VideoThumbChip({ title, channel, duration, badge, tone, size = "md", interactive, onReveal }) {
    const [revealed, setRevealed] = useState(false);
    const toggle = (v) => { setRevealed(v); if (onReveal) onReveal(v); };
    return <div className={`ld-thumb-chip ld-thumb-chip-${size}${interactive ? " ld-thumb-chip-interactive" : ""}`}
        tabIndex={interactive ? 0 : undefined}
        onMouseEnter={interactive ? () => toggle(true) : undefined}
        onMouseLeave={interactive ? () => toggle(false) : undefined}
        onFocus={interactive ? () => toggle(true) : undefined}
        onBlur={interactive ? () => toggle(false) : undefined}>
        <div className="ld-thumb-media">
            <svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
                <rect width="320" height="180" fill="var(--yt-surface)" />
                <polygon points="140,72 140,108 172,90" fill="var(--yt-accent)" opacity=".9" />
            </svg>
            <span className="ld-thumb-duration">{duration}</span>
            {badge && <span className={`ld-thumb-badge${tone ? ` ld-thumb-badge-${tone}` : ""}`}>{badge}</span>}
            {interactive && <span className={`ld-thumb-reveal${revealed ? " visible" : ""}`}>{interactive}</span>}
        </div>
        <div className="ld-thumb-meta">
            <span className="ld-thumb-avatar" aria-hidden="true" />
            <div>
                <strong>{title}</strong>
                <span>{channel}</span>
            </div>
        </div>
    </div>;
}

/* --------------------------------------------------------- hero exhibit */

/* Video Intelligence Forensics: one video, inspected. A real 16:9 frame
   with its identity strip, a scrubber-style timeline carrying the signals
   an analysis pass actually finds (chapters, an engagement peak, a
   sentiment shift, an AI note), and the readout those signals produce. */
function HeroExhibit() {
    return <figure className="ld-forensics">
        <div className="ld-forensics-frame">
            <svg viewBox="0 0 400 225" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
                <defs>
                    <linearGradient id="ld-thumb-grad" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stopColor="var(--yt-surface-alt)" />
                        <stop offset="100%" stopColor="var(--yt-surface)" />
                    </linearGradient>
                </defs>
                <rect width="400" height="225" fill="url(#ld-thumb-grad)" />
                {[...Array(9)].map((_, i) => <line key={i} x1={i * 44 + 20} y1="0" x2={i * 44 + 20} y2="225" stroke="var(--yt-border)" strokeWidth="1" opacity=".4" />)}
                <polygon points="176,90 176,135 214,112.5" fill="var(--yt-accent)" opacity=".92" />
            </svg>
            <span className="ld-forensics-duration">07:42</span>
            <span className="ld-forensics-scan"><span className="ld-pulse-dot"><span className="ld-pulse-ring" /></span>Inspecting</span>
        </div>
        <div className="ld-forensics-meta">
            <span className="ld-thumb-avatar" aria-hidden="true" />
            <div>
                <strong>“How I Edit Faster”</strong>
                <span>Reel Oracle demo channel · published 3 days ago</span>
            </div>
        </div>
        <div className="ld-forensics-timeline">
            <div className="ld-forensics-track">
                <span className="ld-forensics-chapter" style={{ left: "18%" }} />
                <span className="ld-forensics-chapter" style={{ left: "34%" }} />
                <span className="ld-forensics-chapter" style={{ left: "58%" }} />
                <span className="ld-forensics-chapter" style={{ left: "83%" }} />
                <span className="ld-forensics-peak" style={{ left: "58%" }} title="Engagement peak" />
                <span className="ld-forensics-shift" style={{ left: "72%" }} title="Sentiment shift" />
                <span className="ld-forensics-insight" style={{ left: "88%" }} title="AI insight">AI</span>
                <span className="ld-forensics-playhead" style={{ left: "42%" }} />
            </div>
            <div className="ld-forensics-track-labels">
                <span>00:00</span>
                <span className="ld-forensics-now">03:14</span>
                <span>07:42</span>
            </div>
        </div>
        <div className="ld-forensics-signals">
            <DataStat value="+38%" label="View velocity" tone="accent" />
            <DataStat value="82" label="Audience sentiment" />
            <DataStat value="04:17" label="Retention risk" tone="warn" />
        </div>
        <figcaption className="ld-caption ld-forensics-caption"><SampleTag /> A real scan reads this video's own retention curve and comments.</figcaption>
    </figure>;
}

/* -------------------------------------------------------------- intake */

const MODES = [
    { id: "video", label: "Analyze video", placeholder: "Paste a video URL or ID", tab: "analyse", field: "videoInput" },
    { id: "channel", label: "Analyze channel", placeholder: "Paste a channel URL or ID", tab: "analyse", field: "auditChannelId" },
    { id: "topic", label: "Discover topics", placeholder: "A topic, product, or event", tab: "discover", field: "topics" },
    { id: "compare", label: "Compare creators", placeholder: "Your channel ID", placeholder2: "Competitor channel ID", tab: "discover", field: "compare" },
];

function IntakeInstrument({ onOpenApp }) {
    const [modeIdx, setModeIdx] = useState(0);
    const mode = MODES[modeIdx];
    const [value, setValue] = useState("");
    const [value2, setValue2] = useState("");
    const [myChannel, setMyChannel] = useMyChannelLanding();
    const railRef = useRef(null);
    const btnRefs = useRef([]);
    const [indicator, setIndicator] = useState({ left: 0, top: 0, width: 0 });

    useEffect(() => {
        const el = btnRefs.current[modeIdx];
        const rail = railRef.current;
        const sync = () => {
            if (!el || !rail) return;
            const r = el.getBoundingClientRect();
            const railR = rail.getBoundingClientRect();
            setIndicator({ left: r.left - railR.left, top: r.top - railR.top, width: r.width });
        };
        sync();
        window.addEventListener("resize", sync);
        return () => window.removeEventListener("resize", sync);
    }, [modeIdx]);

    const submit = (e) => {
        e.preventDefault();
        const intent = { tab: mode.tab };
        if (mode.id === "compare") {
            if (value) setMyChannel(value);
            intent.competitorIds = value2;
        } else {
            intent[mode.field] = value;
        }
        try { sessionStorage.setItem("yt-landing-intent", JSON.stringify(intent)); } catch { /* opens without prefill */ }
        onOpenApp();
    };

    const selectMode = (i) => { setModeIdx(i); setValue(""); setValue2(""); };

    const onModesKeyDown = (e) => {
        let next = null;
        if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (modeIdx + 1) % MODES.length;
        else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (modeIdx - 1 + MODES.length) % MODES.length;
        else if (e.key === "Home") next = 0;
        else if (e.key === "End") next = MODES.length - 1;
        if (next !== null) {
            e.preventDefault();
            btnRefs.current[next]?.focus();
            selectMode(next);
        }
    };

    return <form className="ld-instrument" onSubmit={submit}>
        <div className="ld-instrument-head">
            <span className="ld-instrument-label">Analysis instrument</span>
            <span className="ld-instrument-hint">No sign-up — runs against the real YouTube Data API</span>
        </div>
        <div className="ld-instrument-modes" role="radiogroup" aria-label="Analysis mode" ref={railRef} onKeyDown={onModesKeyDown}>
            <span className="ld-instrument-indicator" style={{ transform: `translate(${indicator.left}px, ${indicator.top}px) scaleX(${indicator.width})` }} />
            {MODES.map((m, i) => <button type="button" key={m.id} ref={(el) => { btnRefs.current[i] = el; }} role="radio" aria-checked={modeIdx === i}
                tabIndex={modeIdx === i ? 0 : -1}
                className={modeIdx === i ? "active" : ""}
                onClick={() => selectMode(i)}>{m.label}</button>)}
        </div>
        <div className={`ld-instrument-fields${mode.id === "compare" ? " ld-instrument-fields-double" : ""}`}>
            <input value={value} onChange={(e) => setValue(e.target.value)} placeholder={mode.id === "compare" ? (mode.placeholder + (myChannel ? ` (saved: ${myChannel})` : "")) : mode.placeholder} aria-label={mode.placeholder} />
            <div className="ld-instrument-field-2">
                <input value={value2} onChange={(e) => setValue2(e.target.value)} placeholder={mode.placeholder2 || ""} aria-label={mode.placeholder2 || "competitor"} tabIndex={mode.id === "compare" ? 0 : -1} />
            </div>
            <button type="submit">Run</button>
        </div>
    </form>;
}

/* --------------------------------------------------------- pillar files */

const DISCOVERY_TOPICS = [
    { label: "AI editing tools, explained fast", channel: "3 channels covering this", duration: "8:14", momentum: 88, size: "lg" },
    { label: "Match reaction, same night", channel: "12 channels covering this", duration: "14:02", momentum: 62, size: "sm" },
    { label: "Budget home studio setup", channel: "2 channels covering this", duration: "11:47", momentum: 30, size: "sm" },
    { label: "Season recap, deep dive", channel: "5 channels covering this", duration: "22:10", momentum: 70, size: "md" },
    { label: "Transfer news roundup", channel: "9 channels covering this", duration: "6:33", momentum: 52, size: "sm" },
    { label: "Why nobody's covered this yet", channel: "0 channels covering this", duration: "—", momentum: 81, size: "md" },
];

function DiscoveryBoard() {
    return <div className="ld-workspace ld-workspace-discover">
        <div className="ld-discovery-board">
            {DISCOVERY_TOPICS.map((t, i) => <div className="ld-discovery-slot" key={t.label} style={{ "--i": i }}>
                <VideoThumbChip title={t.label} channel={t.channel} duration={t.duration} size={t.size}
                    badge={t.momentum > 75 ? "BURST" : null} tone="alert"
                    interactive={`+${t.momentum}% velocity`} />
            </div>)}
        </div>
        <div className="ld-emerging">
            <span className="ld-module-head">Emerging searches</span>
            <div className="ld-emerging-row">
                {DISCOVERY_TOPICS.slice().sort((a, b) => b.momentum - a.momentum).map((t) => <span key={t.label} className="ld-emerging-chip">
                    {t.label.split(",")[0]}<i>+{t.momentum}%</i>
                </span>)}
            </div>
        </div>
        <Illustrative>Trend Radar plots burst z-score against each topic's own baseline; content-gap analysis runs against named competitors.</Illustrative>
    </div>;
}

function VideoWorkspace() {
    return <div className="ld-workspace ld-workspace-analyse">
        <div className="ld-channel-strip">
            <span className="ld-thumb-avatar" aria-hidden="true" />
            <div>
                <strong>Reel Oracle demo channel</strong>
                <span>212K subscribers · uploads 2×/week</span>
            </div>
        </div>
        <div className="ld-forensic-thumb">
            <svg viewBox="0 0 400 225" preserveAspectRatio="xMidYMid slice">
                <rect width="400" height="225" fill="var(--yt-surface)" />
                <polygon points="176,90 176,135 214,112.5" fill="var(--yt-accent)" />
                <line x1="0" y1="90" x2="400" y2="90" stroke="var(--yt-border)" strokeWidth="1" opacity=".5" />
                <line x1="0" y1="135" x2="400" y2="135" stroke="var(--yt-border)" strokeWidth="1" opacity=".5" />
            </svg>
            <span className="ld-forensic-tag">“How I Edit Faster” · 00:07:42</span>
        </div>
        <div className="ld-forensic-timeline">
            <span className="ld-module-head">Engagement timeline</span>
            <div className="ld-timeline-track">
                {[8, 22, 61, 30, 88, 45, 15, 70].map((v, i) => <div key={i} className="ld-timeline-bar" style={{ height: `${v}%` }} />)}
                <div className="ld-timeline-marker" style={{ left: "58%" }}><span>Hook lands</span></div>
                <div className="ld-timeline-marker" style={{ left: "82%" }}><span>Drop-off risk</span></div>
            </div>
            <blockquote className="ld-transcript-fragment">
                <span className="ld-caption">TRANSCRIPT · 00:04:12</span>
                “...and that's the one setting that changed everything for me...”
            </blockquote>
        </div>
        <div className="ld-forensic-sentiment">
            <span className="ld-module-head">Sentiment distribution</span>
            <div className="ld-sentiment-bar">
                <span style={{ width: "64%", background: "var(--yt-success-text)" }} />
                <span style={{ width: "24%", background: "var(--yt-text-dim)" }} />
                <span style={{ width: "12%", background: "var(--yt-danger-text)" }} />
            </div>
            <div className="ld-sentiment-legend"><span>Positive 64%</span><span>Neutral 24%</span><span>Negative 12%</span></div>
        </div>
        <div className="ld-forensic-stats">
            <DataStat value="7.6/10" label="Virality score" />
            <DataStat value="4.9%" label="Engagement rate" />
            <DataStat value="3" label="AI observations" />
        </div>
        <Illustrative>A real run reads the actual video's comments, thumbnail and engagement curve.</Illustrative>
    </div>;
}

function ForecastPanel() {
    const [showBand, setShowBand] = useState(false);
    const toggle = (v) => () => setShowBand(v);
    return <div className="ld-workspace ld-workspace-predict">
        <div className="ld-forecast-context">
            <span className="ld-caption">PREDICTING</span>
            <strong>“How I Edit Faster” — next 7 days</strong>
        </div>
        <div className="ld-forecast-hero">
            <svg viewBox="0 0 400 220" className="ld-forecast-chart" role="img" aria-label="Forecast trajectory for this video, with a confidence band revealed on hover or focus, illustrative">
                <line x1="20" y1="180" x2="380" y2="180" stroke="var(--yt-border)" strokeWidth="1" />
                <polyline points="20,160 90,140 140,125 180,108" fill="none" stroke="var(--yt-text-dim)" strokeWidth="2" />
                <g className="ld-forecast-focusable" tabIndex={0}
                    onMouseEnter={toggle(true)} onMouseLeave={toggle(false)}
                    onFocus={toggle(true)} onBlur={toggle(false)}>
                    <polygon className={`ld-forecast-band${showBand ? " visible" : ""}`}
                        points="180,108 240,86 300,58 380,20 380,88 300,110 240,128 180,140" fill="var(--yt-accent-soft)" />
                    <polyline points="180,108 240,90 300,62 380,20" fill="none" stroke="var(--yt-accent)" strokeWidth="2.5" strokeDasharray="7 5" className="ld-forecast-line" style={{ "--yt-draw-length": 260 }} />
                    <rect x="150" y="4" width="230" height="216" fill="transparent" />
                </g>
                <circle cx="180" cy="108" r="4" fill="var(--yt-text-primary)" />
                <text x="184" y="100" className="ld-forecast-now">NOW</text>
                <text x="380" y="34" textAnchor="end" className={`ld-forecast-band-label${showBand ? " visible" : ""}`}>68–96 range</text>
            </svg>
            <div className="ld-forecast-readout">
                <DataStat value="82" label="Predicted score" tone="accent" />
                <div className="ld-forecast-confidence">
                    <span className="ld-caption">Model confidence</span>
                    <strong>0.76</strong>
                    <span className="ld-forecast-hint">Hover or focus the chart for the confidence range</span>
                </div>
            </div>
        </div>
        <p className="ld-illustrative"><SampleTag /> Predict runs a heuristic score immediately, or trains a RandomForest/ARIMA model once there's tracked history.</p>
    </div>;
}

function TitleStack() {
    const titles = [
        { text: "Why nobody talks about this until it's too late", ctr: "High", risk: "Low" },
        { text: "I tested every budget option so you don't have to", ctr: "Med", risk: "Low" },
        { text: "The setup mistake costing you views", ctr: "High", risk: "Med" },
    ];
    return <div className="ld-workspace ld-workspace-create">
        <span className="ld-module-head">Title variants</span>
        <div className="ld-galley">
            {titles.map((t, i) => <div className="ld-galley-strip" key={t.text} style={{ "--i": i }}>
                <span className="ld-galley-n">{String(i + 1).padStart(2, "0")}</span>
                <p>{t.text}</p>
                <div className="ld-galley-tags">
                    <span className="ld-galley-tag">CTR {t.ctr}</span>
                    <span className="ld-galley-tag ld-galley-tag-muted">Clickbait {t.risk}</span>
                </div>
            </div>)}
        </div>
        <span className="ld-module-head">Hook angles</span>
        <div className="ld-hooks">
            <span>Contrarian claim</span><span>Cost comparison</span><span>Before/after</span><span>Common mistake</span>
        </div>
        <Illustrative>The real generator scores your own topic for predicted CTR class and clickbait risk.</Illustrative>
    </div>;
}

const MONITOR_EVENTS = [
    { t: "14:02", subject: "“How I Edit Faster” — comments", note: "Sentiment holding at 91% positive, sample of 50", kind: "ok" },
    { t: "13:48", subject: "Tracked channel — upload cadence", note: "No anomalies against the channel's own baseline", kind: "ok" },
    { t: "13:20", subject: "“Season Recap” — live chat", note: "Toxicity crossed the 15% alert threshold", kind: "alert" },
    { t: "12:55", subject: "“Budget Setup Tour” — views/day", note: "2.1× the channel's baseline rate — flagged as an outlier", kind: "watch" },
    { t: "12:30", subject: "Tracked channel — snapshot", note: "Subscriber count and avg views/day recorded", kind: "ok" },
];

function MonitorStream() {
    return <div className="ld-workspace ld-workspace-monitor">
        <div className="ld-monitor-head">
            <span className="ld-stamp ld-stamp-live"><span className="ld-pulse-dot"><span className="ld-pulse-ring" /></span>Sample data</span>
            <span className="ld-module-head">What monitoring watches for</span>
        </div>
        <ol className="ld-event-stream">
            {MONITOR_EVENTS.map((e) => <li key={e.t + e.subject} className={`ld-event ld-event-${e.kind}`}>
                <span className="ld-event-time">{e.t}</span>
                <span className="ld-event-marker" aria-hidden="true" />
                <div className="ld-event-body">
                    <strong>{e.subject}</strong>
                    <p>{e.note}</p>
                </div>
                <span className="ld-event-kind">{e.kind === "alert" ? "Alert" : e.kind === "watch" ? "Watching" : "Clear"}</span>
            </li>)}
        </ol>
        <p className="ld-illustrative">Not a live connection — Monitor re-polls comments, live chat and upload cadence on demand.</p>
    </div>;
}

function effortWord(v) {
    return v <= 33 ? "Low" : v <= 66 ? "Medium" : "High";
}

function DecisionMeter({ label, value, display }) {
    return <div className="ld-meter">
        <div className="ld-meter-head"><span>{label}</span><strong>{display}</strong></div>
        <div className="ld-meter-track" role="meter" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
            <i style={{ width: `${value}%` }} />
        </div>
    </div>;
}

function DecisionList() {
    const recs = [
        { title: "Cover the AI-editing gap", channel: "Your channel", reason: "3 competitors published this week, you haven't.", impact: 90, effort: 30, confidence: 80 },
        { title: "Re-cut your best hook into a Short", channel: "“How I Edit Faster”", reason: "Highest retention moment in your last upload.", impact: 70, effort: 20, confidence: 65 },
        { title: "Publish Tuesday 14:00 UTC", channel: "Your channel", reason: "Your own upload-timing history's best window.", impact: 45, effort: 5, confidence: 72 },
    ];
    return <div className="ld-workspace ld-workspace-recommend">
        <ol className="ld-decisions">
            {recs.map((r, i) => <li key={r.title}>
                <span className="ld-decisions-rank">{i + 1}</span>
                <div className="ld-decisions-body">
                    <span className="ld-decisions-for">For: {r.channel}</span>
                    <strong>{r.title}</strong>
                    <p>{r.reason}</p>
                    <div className="ld-decisions-meters">
                        <DecisionMeter label="Impact" value={r.impact} display={`${r.impact}/100`} />
                        <DecisionMeter label="Effort" value={r.effort} display={effortWord(r.effort)} />
                        <DecisionMeter label="Confidence" value={r.confidence} display={`${r.confidence}%`} />
                    </div>
                </div>
            </li>)}
        </ol>
        <Illustrative>Real ideas are ranked the same way, from your own content-gap analysis against named competitors.</Illustrative>
    </div>;
}

const PERFORMANCE_STAGES = [
    { stage: "Video published", metric: "Aug 2", note: "07:42 runtime, cold start" },
    { stage: "Initial velocity", metric: "1.2K/hr", note: "views in the first 24h" },
    { stage: "Engagement shift", metric: "+14pt", note: "retention after the hook re-cut" },
    { stage: "Algorithm momentum", metric: "3.4×", note: "suggested traffic vs. baseline" },
    { stage: "Current performance", metric: "58.6K", note: "+372% vs. this channel's average" },
];

function PerformanceHistory() {
    return <div className="ld-performance-flow">
        {PERFORMANCE_STAGES.map((s, i) => <div className="ld-performance-stage" key={s.stage}>
            <div className="ld-performance-body">
                <span className="ld-caption">{s.stage}</span>
                <strong>{s.metric}</strong>
                <span className="ld-performance-note">{s.note}</span>
            </div>
            {i < PERFORMANCE_STAGES.length - 1 && <span className="ld-performance-arrow" aria-hidden="true">
                <svg width="20" height="12" viewBox="0 0 20 12" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M1 6h16M12 1l6 5-6 5" /></svg>
            </span>}
        </div>)}
    </div>;
}

function MilestoneTimeline() {
    return <div className="ld-workspace ld-workspace-tracking">
        <span className="ld-module-head">Performance history — one video, published to now</span>
        <PerformanceHistory />
        <Illustrative>A real channel's stages come from the snapshot history the background poller builds once you track it.</Illustrative>
    </div>;
}

/* --------------------------------------------------------------- files */

const PILLARS = [
    { id: "discover", code: "01", label: "Discover", thesis: "Find what's moving before the rest of the internet notices.", Body: DiscoveryBoard },
    { id: "analyse", code: "02", label: "Analyse", thesis: "Turn one video into a verdict, with the evidence attached.", Body: VideoWorkspace },
    { id: "predict", code: "03", label: "Predict", thesis: "A heuristic score today, a trained model once there's history.", Body: ForecastPanel },
    { id: "create", code: "04", label: "Create", thesis: "Decide what to publish next, and how to title it.", Body: TitleStack },
    { id: "monitor", code: "05", label: "Monitor", thesis: "Watch sentiment and performance while it's still happening.", Body: MonitorStream },
    { id: "recommend", code: "06", label: "Recommend", thesis: "Close the loop from research to the next thing you make.", Body: DecisionList },
    { id: "tracking", code: "07", label: "Tracking", thesis: "The persistence layer everything else quietly depends on.", Body: MilestoneTimeline },
];

function PillarFile({ pillar }) {
    const { code, label, thesis, Body } = pillar;
    return <div className="ld-file">
        <div className="ld-file-head">
            <span className="ld-caption">RO-{code} · {label.toUpperCase()}</span>
            <h2 className="ld-section-head">{thesis}</h2>
        </div>
        <Body />
    </div>;
}

const INQUIRIES = [
    { q: "What should I make next?", draws: ["01", "Discover"], evidence: "Rising topics flagged before they saturate — Trend Radar's burst z-score against each topic's own baseline." },
    { q: "Why did this video outperform the last one?", draws: ["02", "Analyse"], evidence: "Engagement, comments, timing and content signals collapsed into one verdict instead of four tabs." },
    { q: "Is something going wrong right now?", draws: ["05", "Monitor"], evidence: "Anomaly detection and live-chat sentiment flag a spike or a hostile pile-on while it's still happening." },
    { q: "Which content gap is worth a title?", draws: ["06", "Recommend"], evidence: "Content gaps become suggested titles; upload-timing history becomes a publish window." },
];

function UseCaseFile() {
    return <div className="ld-file">
        <div className="ld-file-head">
            <span className="ld-caption">RO-08 · MISSION</span>
            <h2 className="ld-section-head">Four questions this replaces four separate tabs for.</h2>
        </div>
        <div className="ld-inquiries">
            {INQUIRIES.map((d) => <div className="ld-inquiry" key={d.q}>
                <p className="ld-inquiry-q">{d.q}</p>
                <div className="ld-inquiry-evidence">
                    <p>{d.evidence}</p>
                    <span className="ld-inquiry-source">RO-{d.draws[0]} · {d.draws[1]}</span>
                </div>
            </div>)}
        </div>
    </div>;
}

const PIPELINE = [
    { label: "YouTube source", note: "Data API v3" },
    { label: "Collection", note: "search, videos, comments" },
    { label: "Normalization", note: "engagement, timing" },
    { label: "AI / ML analysis", note: "NLP, RandomForest, ARIMA" },
    { label: "Intelligence", note: "scored, cited findings" },
    { label: "Decision", note: "what to publish next" },
];

function PipelineFile() {
    const ref = useRef(null);
    const [active, setActive] = useState(false);
    useEffect(() => {
        const t = requestAnimationFrame(() => setActive(true));
        return () => cancelAnimationFrame(t);
    }, []);
    return <div className="ld-file" ref={ref}>
        <div className="ld-file-head">
            <span className="ld-caption">RO-09 · CHAIN OF CUSTODY</span>
            <h2 className="ld-section-head">A pasted link becomes a verdict in six transformations.</h2>
        </div>
        <div className={`ld-pipeline${active ? " ld-pipeline-active" : ""}`}>
            {PIPELINE.map((n, i) => <div className="ld-pipeline-node" key={n.label} style={{ "--i": i }}>
                <span className="ld-pipeline-dot" />
                <strong>{n.label}</strong>
                <span>{n.note}</span>
                {i < PIPELINE.length - 1 && <svg className="ld-pipeline-connector" viewBox="0 0 60 4" preserveAspectRatio="none" aria-hidden="true"><line x1="0" y1="2" x2="60" y2="2" stroke="var(--yt-border-strong)" strokeWidth="2" /></svg>}
            </div>)}
        </div>
    </div>;
}

const LOG_ENTRIES = [
    { k: "Data source", v: "YouTube Data API v3, queried live at request time" },
    { k: "Trained models", v: "RandomForest (virality), ARIMA (subscriber growth)" },
    { k: "NLP", v: "Sentiment, aspect extraction, bot-risk, multilingual, TF-IDF re-ranking" },
    { k: "Stack", v: "FastAPI + React/Vite, deployed on Render + Vercel" },
];

function LogFile({ onOpenApp }) {
    return <div className="ld-file ld-file-log">
        <div className="ld-file-head">
            <span className="ld-caption">RO-10 · CASE LOG</span>
            <h2 className="ld-section-head">What's actually running under this.</h2>
        </div>
        <dl className="ld-log-list">
            {LOG_ENTRIES.map((e) => <div className="ld-log-row" key={e.k}><dt>{e.k}</dt><dd>{e.v}</dd></div>)}
        </dl>
        <div className="ld-closing">
            <h3 className="ld-closing-head">The next case is whatever you paste in.</h3>
            <button className="ld-cta-primary" onClick={onOpenApp}>Discover your next topic</button>
            <span className="ld-caption ld-closing-meta">Reel Oracle · Field Intelligence Dossier · RO-INTEL</span>
        </div>
    </div>;
}

/* ------------------------------------------------------------- overview */

function OverviewFile({ onOpenApp, onSelectFile }) {
    return <div className="ld-file ld-file-overview">
        <div className="ld-overview-copy">
            <span className="ld-stamp">Case File</span>
            <h2 className="ld-hero-display">Reel Oracle turns a YouTube channel into a case file.</h2>
            <p className="ld-lead">Discover, analyse, predict, create, monitor, recommend and track — seven intelligence pillars on the real YouTube Data API, heuristic scoring, trained ML models and NLP. Not a mockup: every verdict here is the actual tool.</p>
            <div className="ld-overview-ctas">
                <button className="ld-cta-primary" onClick={onOpenApp}>Open the live briefing</button>
                <button type="button" className="ld-cta-secondary" onClick={() => onSelectFile("method")}>See how it works</button>
            </div>
        </div>
        <div className="ld-overview-right">
            <HeroExhibit />
            <IntakeInstrument onOpenApp={onOpenApp} />
        </div>
    </div>;
}

/* ------------------------------------------------------------------ nav */

function LandingNav({ theme, onToggleTheme, onOpenApp }) {
    const [scrolled, setScrolled] = useState(false);
    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 8);
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, []);
    return <header className={`ld-nav${scrolled ? " ld-nav-scrolled" : ""}`}>
        <span className="ld-wordmark"><span className="ld-wordmark-mark">RO</span>Reel Oracle</span>
        <div className="ld-nav-right">
            <span className="ld-nav-meta">RO-INTEL · LIVE DEMO</span>
            <button className="ld-theme-toggle" onClick={onToggleTheme} aria-label="Toggle theme">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true" className="ld-theme-icon">
                    <circle cx="12" cy="12" r="4.5" className="ld-theme-sun" style={{ opacity: theme === "dark" ? 1 : 0, transform: theme === "dark" ? "rotate(0deg) scale(1)" : "rotate(-90deg) scale(.4)" }} />
                    <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5Z" className="ld-theme-moon" style={{ opacity: theme === "dark" ? 0 : 1, transform: theme === "dark" ? "rotate(90deg) scale(.4)" : "rotate(0deg) scale(1)" }} />
                </svg>
            </button>
            <button className="ld-cta-nav" onClick={onOpenApp}>Open the live briefing</button>
        </div>
    </header>;
}

/* --------------------------------------------------------------- drawer */

const FILES = [
    { id: "overview", code: "00", label: "Overview" },
    ...PILLARS.map((f) => ({ id: f.id, code: f.code, label: f.label })),
    { id: "who", code: "08", label: "Mission" },
    { id: "method", code: "09", label: "Method" },
    { id: "log", code: "10", label: "Log" },
];

function CaseDrawer({ active, onSelect, tablistId, panelId }) {
    const btnRefs = useRef([]);
    const railRef = useRef(null);
    const [edge, setEdge] = useState({ start: false, end: true });

    const checkEdges = () => {
        const el = railRef.current;
        if (!el) return;
        setEdge({ start: el.scrollLeft > 4, end: el.scrollLeft < el.scrollWidth - el.clientWidth - 4 });
    };
    useEffect(() => { checkEdges(); window.addEventListener("resize", checkEdges); return () => window.removeEventListener("resize", checkEdges); }, []);

    const activeIdx = FILES.findIndex((f) => f.id === active);
    const onKeyDown = (e) => {
        const focusedIdx = btnRefs.current.indexOf(document.activeElement);
        const fromIdx = focusedIdx >= 0 ? focusedIdx : activeIdx;
        let next = null;
        if (e.key === "ArrowRight") next = (fromIdx + 1) % FILES.length;
        else if (e.key === "ArrowLeft") next = (fromIdx - 1 + FILES.length) % FILES.length;
        else if (e.key === "Home") next = 0;
        else if (e.key === "End") next = FILES.length - 1;
        else if (e.key === "Enter" || e.key === " ") { onSelect(FILES[fromIdx].id); return; }
        if (next !== null) {
            e.preventDefault();
            btnRefs.current[next]?.focus();
            onSelect(FILES[next].id);
        }
    };

    return <div className="ld-drawer-shell">
        <nav className="ld-drawer-rail" role="tablist" id={tablistId} aria-label="Case files" ref={railRef} onScroll={checkEdges} onKeyDown={onKeyDown}>
            {FILES.map((f, i) => <button key={f.id} id={`${tablistId}-${f.id}`} role="tab" aria-selected={active === f.id} aria-controls={panelId}
                tabIndex={active === f.id ? 0 : -1} ref={(el) => { btnRefs.current[i] = el; }}
                className={active === f.id ? "active" : ""} onClick={() => onSelect(f.id)}>
                <span className="ld-drawer-code" aria-hidden="true">{f.code}</span>{f.label}
            </button>)}
        </nav>
        <span className={`ld-drawer-fade ld-drawer-fade-start${edge.start ? " visible" : ""}`} aria-hidden="true" />
        <span className={`ld-drawer-fade ld-drawer-fade-end${edge.end ? " visible" : ""}`} aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 3l6 5-6 5" /></svg>
        </span>
    </div>;
}

/* -------------------------------------------------------------- landing */

function Landing({ theme, onToggleTheme, onNavigate }) {
    const [active, setActive] = useState("overview");
    const [firstPaint, setFirstPaint] = useState(true);
    const openApp = () => onNavigate("/app");
    const reactId = useId();
    const tablistId = `ld-tabs-${reactId}`;
    const panelId = `ld-panel-${reactId}`;

    useEffect(() => {
        const t = setTimeout(() => setFirstPaint(false), 600);
        return () => clearTimeout(t);
    }, []);

    const pillar = PILLARS.find((f) => f.id === active);

    return <div className="ld-page">
        <a className="ld-skip-link" href="#main-content">Skip to case file</a>
        <LandingNav theme={theme} onToggleTheme={onToggleTheme} onOpenApp={openApp} />
        <h1 className="yt-sr-only">Reel Oracle</h1>
        <main className="ld-drawer" id="main-content">
            <CaseDrawer active={active} onSelect={setActive} tablistId={tablistId} panelId={panelId} />
            <div className={`ld-file-viewport${firstPaint ? " ld-file-viewport-first" : " ld-file-viewport-switch"}`}
                role="tabpanel" id={panelId} aria-labelledby={`${tablistId}-${active}`} tabIndex={0} key={active}>
                {active === "overview" && <OverviewFile onOpenApp={openApp} onSelectFile={setActive} />}
                {pillar && <PillarFile pillar={pillar} />}
                {active === "who" && <UseCaseFile />}
                {active === "method" && <PipelineFile />}
                {active === "log" && <LogFile onOpenApp={openApp} />}
            </div>
        </main>
        <footer className="yt-sr-only">Reel Oracle · Field Intelligence Dossier · RO-INTEL</footer>
    </div>;
}

export default Landing;
