import { useEffect, useRef, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

import Loader from "../components/Loader";
import {
    getYoutubeStatus, getTrendRadar, getOpportunities, getCompetitors, getVideoCategories,
    getI18nRegions, getChannelSections, getLiveNow, getUpcoming,
    getCreatorNetwork, getTopicIntelligence, semanticSearch,
    analyzeVideo, analyzeThumbnail, analyzeAspects, analyzeMisleading, analyzeBrandSafety, analyzePlaylist,
    analyzeBotRisk, analyzeChannelAudit,
    predictVirality, predictChannelGrowth, predictViralityMl, predictChannelGrowthMl,
    createTitles, getUploadTiming, getPersonalizedInsights,
    monitorSentiment, monitorAnomalies, monitorLiveChat,
    recommendSimilar, recommendNextVideoIdeas,
    trackChannel, listTrackedChannels, untrackChannel,
    trackVideo, listTrackedVideos, untrackVideo,
    getChannelHistory, getVideoHistory, getTrackingDigest,
    channelHistoryCsvUrl, videoHistoryCsvUrl,
    getChannelLeaderboard, getVideoLeaderboard, getTrackingMilestones, compareChannels, getContentCalendar,
    getOAuthStatus, getOAuthAuthorizeUrl, disconnectOAuth, getOAuthAnalytics,
} from "../api/youtubeApi";
import { WS_BASE_URL } from "../api/apiClient";
import "./YoutubeIntel.css";

const TABS = [
    { id: "overview", label: "Overview" },
    { id: "discover", label: "Discover" },
    { id: "analyse", label: "Analyse" },
    { id: "predict", label: "Predict" },
    { id: "create", label: "Create" },
    { id: "monitor", label: "Monitor" },
    { id: "recommend", label: "Recommend" },
    { id: "tracking", label: "Tracking" },
];

function extractVideoId(input) {
    const value = (input || "").trim();
    const match = value.match(/(?:v=|youtu\.be\/|shorts\/)([\w-]{11})/);
    return match ? match[1] : value;
}

// Pulls a channel ID, @handle, or legacy username out of a pasted URL so it
// can travel safely as a URL *path* segment (a raw URL's own slashes would
// otherwise collide with routing) - the backend resolves whatever comes out
// of this (an @handle or username still needs one lookup) into a real ID.
function extractChannelId(input) {
    const value = (input || "").trim();
    let match = value.match(/youtube\.com\/channel\/(UC[\w-]{22})/);
    if (match) return match[1];
    match = value.match(/youtube\.com\/@([\w.-]+)/);
    if (match) return `@${match[1]}`;
    match = value.match(/youtube\.com\/(?:c|user)\/([\w.-]+)/);
    if (match) return match[1];
    return value;
}

function extractChannelIdsCsv(input) {
    return (input || "").split(",").map((v) => extractChannelId(v)).filter(Boolean).join(",");
}

function useMyChannel() {
    const [value, setValue] = useState(() => localStorage.getItem("yt-my-channel") || "");
    const set = (next) => {
        setValue(next);
        if (next) localStorage.setItem("yt-my-channel", next);
        else localStorage.removeItem("yt-my-channel");
    };
    return [value, set];
}

function useAsync() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [data, setData] = useState(null);
    const run = async (fn) => {
        setLoading(true); setError(""); setData(null);
        try { setData(await fn()); } catch (err) {
            setError(err?.response?.data?.detail || "Request failed.");
        } finally { setLoading(false); }
    };
    return { loading, error, data, run, setData };
}

const LIVE_CHAT_MAX_POINTS = 40;

// Drives the /ws/monitor/live-chat/{id} WebSocket. Free and quota-safe by
// construction: nothing polls until start() opens a connection, and the
// backend never runs the loop without one open - stop() (and unmount)
// always sends an explicit stop message before closing rather than just
// dropping the socket, so the server can end the session immediately
// instead of relying on TCP disconnect detection (which the backend can't
// count on being prompt). A hard session-length cap on the server is the
// backstop if a tab is ever killed ungracefully instead of stopped.
function useLiveChatMonitor() {
    const [status, setStatus] = useState("idle"); // idle | connecting | live | ended
    const [ticks, setTicks] = useState([]);
    const [endReason, setEndReason] = useState(null);
    const socketRef = useRef(null);

    const stop = () => {
        const ws = socketRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
            try { ws.send("stop"); } catch { /* closing anyway */ }
        }
        if (ws) ws.close();
        socketRef.current = null;
        setStatus((s) => (s === "idle" ? s : "ended"));
    };

    const start = (videoId) => {
        stop();
        setTicks([]);
        setEndReason(null);
        setStatus("connecting");

        const ws = new WebSocket(`${WS_BASE_URL}/ws/monitor/live-chat/${encodeURIComponent(videoId)}`);
        socketRef.current = ws;

        ws.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            if (payload.type === "tick") {
                setStatus("live");
                setTicks((prev) => [...prev.slice(-(LIVE_CHAT_MAX_POINTS - 1)), payload]);
            } else if (payload.type === "session_ended") {
                setStatus("ended");
                setEndReason(payload.reason);
            }
        };
        ws.onerror = () => setStatus((s) => (s === "connecting" ? "ended" : s));
        ws.onclose = () => { if (socketRef.current === ws) socketRef.current = null; };
    };

    useEffect(() => () => stop(), []);

    return { status, ticks, latest: ticks[ticks.length - 1] || null, endReason, start, stop };
}

function Field({ label, ...props }) {
    return <label className="yt-field"><span>{label}</span><input {...props} /></label>;
}

function Panel({ title, children, className }) {
    return <div className={`yt-panel-block${className ? ` ${className}` : ""}`}><h3>{title}</h3>{children}</div>;
}

function DirectionIcon({ direction }) {
    return <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden="true" style={{ verticalAlign: "middle" }}>
        {direction === "spike" ? <path d="M5 1 L9 8 L1 8 Z" /> : <path d="M5 9 L1 2 L9 2 Z" />}
    </svg>;
}

const LIVE_CHAT_END_MESSAGES = {
    not_live: "This video isn't currently live (or the stream has ended).",
    time_limit: "Session time limit reached — click Go live to start a fresh session.",
    quota_budget_reached: "Today's YouTube quota budget is used up — try again after the daily reset.",
    not_configured: "YOUTUBE_API_KEY is not set on the backend.",
    error: "Live session ended unexpectedly — try again.",
};

function LiveVelocityChart({ ticks }) {
    if (ticks.length < 2) return <p className="yt-note">Watching for messages — the chart fills in as chat activity comes in.</p>;
    const gridColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-border").trim() || "#29466f";
    const textColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-text-dim").trim() || "#7690b6";
    const surfaceColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-surface").trim() || "#0d1627";
    const primaryColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-text-primary").trim() || "#f8fafc";
    const accentColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-accent").trim() || "#a3341f";
    return <div className="yt-chart">
        <ResponsiveContainer width="100%" height={140}>
            <LineChart data={ticks}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="elapsed_seconds" stroke={textColor} fontSize={11} tickFormatter={(s) => `${s}s`} />
                <YAxis stroke={textColor} fontSize={11} />
                <Tooltip contentStyle={{ background: surfaceColor, border: `1px solid ${gridColor}`, borderRadius: 8, color: primaryColor }} labelFormatter={(s) => `${s}s in`} />
                <Line type="monotone" dataKey="messages_per_min" name="Messages/min" stroke={accentColor} strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
        </ResponsiveContainer>
    </div>;
}

function StatRow({ items }) {
    return <div className="yt-stat-row">
        {items.map(([label, value]) => <div className="yt-stat" key={label}><span>{label}</span><strong>{value}</strong></div>)}
    </div>;
}

// ----------------------------------------------------------------- Overview

const PILLAR_DIRECTORY = [
    { id: "discover", code: "01", label: "Discover", summary: "Trend radar, content gaps, creator network, topic intelligence, semantic search." },
    { id: "analyse", code: "02", label: "Analyse", summary: "Video intelligence, thumbnail scoring, misleading-title detection, bot-risk, brand safety, channel audit." },
    { id: "predict", code: "03", label: "Predict", summary: "Heuristic and trained-model virality; heuristic and ARIMA channel-growth forecasting." },
    { id: "create", code: "04", label: "Create", summary: "Title generator with CTR/clickbait scoring, best upload timing, personalized title insights." },
    { id: "monitor", code: "05", label: "Monitor", summary: "Poll-based comment sentiment, upload anomaly detection, live-chat sentiment and message velocity." },
    { id: "recommend", code: "06", label: "Recommend", summary: "Similar-video discovery, content-gap-derived next-video ideas." },
    { id: "tracking", code: "07", label: "Tracking", summary: "Track channels/videos, leaderboards, milestone alerts, head-to-head comparisons, CSV export, OAuth analytics." },
];

function OverviewTab({ onSelectTab }) {
    const digest = useAsync();
    const milestones = useAsync();

    useEffect(() => {
        digest.run(() => getTrackingDigest());
        milestones.run(() => getTrackingMilestones(6));
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const trackedCount = (digest.data?.channels.length || 0) + (digest.data?.videos.length || 0);

    return <div className="yt-grid-2">
        <Panel title="Case Directory" className="yt-panel-span-2">
            <p className="yt-note">Seven pillars, one line each — open any of them straight from here.</p>
            <table className="yt-table yt-directory">
                <tbody>
                    {PILLAR_DIRECTORY.map((p) => <tr key={p.id}>
                        <td className="yt-directory-code">{p.code}</td>
                        <td>
                            <button type="button" className="yt-directory-link" onClick={() => onSelectTab(p.id)}>{p.label}</button>
                            <p className="yt-note">{p.summary}</p>
                        </td>
                    </tr>)}
                </tbody>
            </table>
        </Panel>

        <Panel title="Watchlist Snapshot">
            {digest.loading && <Loader label="Loading watchlist" />}
            {digest.error && <p className="yt-error">{digest.error}</p>}
            {digest.data && (trackedCount === 0
                ? <p className="yt-note">Nothing tracked yet — add a channel or video from the Tracking tab to start building history.</p>
                : <ul className="yt-list">
                    {digest.data.channels.slice(0, 3).map((c) => <li key={c.channel_id}>
                        <strong>{c.label || c.channel_id}</strong> — {c.latest_subscribers != null ? `${c.latest_subscribers.toLocaleString()} subscribers` : "no snapshot yet"}
                    </li>)}
                    {digest.data.videos.slice(0, 3).map((v) => <li key={v.video_id}>
                        <strong>{v.label || v.video_id}</strong> — {v.latest_views != null ? `${v.latest_views.toLocaleString()} views` : "no snapshot yet"}
                    </li>)}
                </ul>)}
            <div className="yt-form-row" style={{ marginTop: 10 }}>
                <button type="button" onClick={() => onSelectTab("tracking")}>Open Tracking</button>
            </div>
        </Panel>

        <Panel title="Latest Activity">
            <p className="yt-note">Recent swings across everything tracked — zero additional YouTube quota.</p>
            {milestones.loading && <Loader label="Scanning snapshot history" />}
            {milestones.error && <p className="yt-error">{milestones.error}</p>}
            {milestones.data && (milestones.data.items.length === 0
                ? <p className="yt-note">No notable swings yet — these show up once tracked items have at least two snapshots apart.</p>
                : <ul className="yt-list">
                    {milestones.data.items.map((e, i) => <li key={i}><strong>{e.label}</strong> — {e.message}</li>)}
                </ul>)}
        </Panel>
    </div>;
}

// ---------------------------------------------------------------- Discover

function DiscoverTab({ initial }) {
    const [topics, setTopics] = useState(initial?.topics || "Manchester United, Arsenal, Real Madrid");
    const [regionCode, setRegionCode] = useState("");
    const [categoryId, setCategoryId] = useState("");
    const [categories, setCategories] = useState([]);
    const [regions, setRegions] = useState([]);
    const [videoDuration, setVideoDuration] = useState("");
    const trend = useAsync();

    const [ownId, setOwnId] = useMyChannel();
    const [competitorIds, setCompetitorIds] = useState(initial?.competitorIds || "");
    const gaps = useAsync();
    const competitors = useAsync();

    useEffect(() => {
        getVideoCategories(regionCode || "US").then((d) => setCategories(d.items)).catch(() => setCategories([]));
    }, [regionCode]);

    useEffect(() => {
        getI18nRegions().then((d) => setRegions(d.items)).catch(() => setRegions([]));
    }, []);

    return <div className="yt-grid-2">
        <Panel title="Trend Radar">
            <div className="yt-form-row">
                <Field label="Topics (comma-separated)" value={topics} onChange={(e) => setTopics(e.target.value)} />
            </div>
            <div className="yt-form-row">
                <label className="yt-field"><span>Region (optional)</span>
                    <select value={regionCode} onChange={(e) => setRegionCode(e.target.value)}>
                        <option value="">Any region</option>
                        {regions.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
                    </select>
                </label>
                <label className="yt-field"><span>Category (optional)</span>
                    <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                        <option value="">Any category</option>
                        {categories.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
                    </select>
                </label>
                <label className="yt-field"><span>Length (optional)</span>
                    <select value={videoDuration} onChange={(e) => setVideoDuration(e.target.value)}>
                        <option value="">Any length</option>
                        <option value="short">Short (&lt;4 min)</option>
                        <option value="medium">Medium (4-20 min)</option>
                        <option value="long">Long (&gt;20 min)</option>
                    </select>
                </label>
                <button onClick={() => trend.run(() => getTrendRadar(topics, 15, regionCode, categoryId, videoDuration))} disabled={trend.loading}>Scan</button>
            </div>
            {trend.loading && <Loader label="Scanning trends" />}
            {trend.error && <p className="yt-error">{trend.error}</p>}
            {trend.data?.topics?.map((t) => <div className="yt-card" key={t.topic}>
                <div className="yt-card-head">
                    <strong>{t.topic}</strong>
                    <span style={{ display: "flex", gap: 6 }}>
                        {t.burst_detected && <span className="yt-badge yt-badge-alert">Burst detected</span>}
                        <span className="yt-badge">{t.momentum_score}/100</span>
                    </span>
                </div>
                <StatRow items={[
                    ["Uploads (7d)", t.uploads_last_7d],
                    ["Channels covering", t.unique_channels_covering],
                    ["Views sampled", t.total_views_sampled.toLocaleString()],
                ]} />
                {t.burst_detected && <p className="yt-note">Upload rate spiked to {t.recent_daily_rate}/day vs a {t.baseline_daily_rate}/day baseline (z={t.burst_z_score}).</p>}
            </div>)}
        </Panel>

        <Panel title="Content Gaps &amp; Competitor Comparison">
            <div className="yt-form-row">
                <Field label="Your channel ID" value={ownId} onChange={(e) => setOwnId(e.target.value)} placeholder="UC..." />
                <Field label="Competitor channel IDs (comma-separated)" value={competitorIds} onChange={(e) => setCompetitorIds(e.target.value)} placeholder="UC..., UC..." />
            </div>
            <div className="yt-form-row">
                <button onClick={() => gaps.run(() => getOpportunities(extractChannelId(ownId), extractChannelIdsCsv(competitorIds)))} disabled={gaps.loading || !ownId || !competitorIds}>Find content gaps</button>
                <button onClick={() => competitors.run(() => getCompetitors(extractChannelIdsCsv([ownId, competitorIds].filter(Boolean).join(","))))} disabled={competitors.loading || !ownId}>Compare channels</button>
            </div>
            {(gaps.loading || competitors.loading) && <Loader label="Comparing channels" />}
            {gaps.error && <p className="yt-error">{gaps.error}</p>}
            {gaps.data?.content_gaps?.length > 0 && <ul className="yt-list">
                {gaps.data.content_gaps.map((g) => <li key={g.keyword}><strong>{g.keyword}</strong> — competitors: {g.competitor_mentions}, you: {g.your_mentions}</li>)}
            </ul>}
            {competitors.error && <p className="yt-error">{competitors.error}</p>}
            {competitors.data?.channels?.length > 0 && <table className="yt-table"><thead><tr><th>Channel</th><th>Subs</th><th>Avg views/video</th></tr></thead>
                <tbody>{competitors.data.channels.map((c) => <tr key={c.channel_id}><td>{c.title}</td><td>{c.subscribers.toLocaleString()}</td><td>{c.avg_views_per_video.toLocaleString()}</td></tr>)}</tbody>
            </table>}
        </Panel>

        <ContentCalendarPanel />
        <SemanticSearchPanel />
        <TopicIntelligencePanel />
        <CreatorNetworkPanel />
    </div>;
}

const WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
// scaleX, not width - keeps the bar's layout box constant so resizing it never triggers reflow.
function calendarBarScale(count, max) {
    return count === 0 ? 0 : Math.max(count / max, 0.02);
}

function ContentCalendarPanel() {
    const [channelA, setChannelA] = useState("");
    const [channelB, setChannelB] = useState("");
    const calendar = useAsync();
    const [revealed, setRevealed] = useState(false);

    const run = () => {
        setRevealed(false);
        calendar.run(() => getContentCalendar(extractChannelId(channelA), extractChannelId(channelB)));
    };

    useEffect(() => {
        if (!calendar.data) return;
        const t = setTimeout(() => setRevealed(true), 20);
        return () => clearTimeout(t);
    }, [calendar.data]);

    const maxCount = calendar.data
        ? Math.max(1, ...WEEKDAY_ORDER.flatMap((d) => [
            calendar.data.channel_a.uploads_by_weekday[d] || 0,
            calendar.data.channel_b.uploads_by_weekday[d] || 0,
        ]))
        : 1;

    return <Panel title="Content Calendar (Upload Cadence)">
        <p className="yt-note">Which weekdays each channel actually publishes on — reuses the same recent-uploads call Content Gaps already makes.</p>
        <div className="yt-form-row">
            <Field label="Channel A" value={channelA} onChange={(e) => setChannelA(e.target.value)} placeholder="UC... or URL" />
            <Field label="Channel B" value={channelB} onChange={(e) => setChannelB(e.target.value)} placeholder="UC... or URL" />
            <button onClick={run} disabled={calendar.loading || !channelA || !channelB}>Compare cadence</button>
        </div>
        {calendar.loading && <Loader label="Reading upload history" />}
        {calendar.error && <p className="yt-error">{calendar.error}</p>}
        {calendar.data && <div className="yt-calendar">
            {WEEKDAY_ORDER.map((day) => {
                const a = calendar.data.channel_a.uploads_by_weekday[day] || 0;
                const b = calendar.data.channel_b.uploads_by_weekday[day] || 0;
                return <div className="yt-calendar-row" key={day}>
                    <span className="yt-calendar-day">{day.slice(0, 3)}</span>
                    <div className="yt-calendar-bars">
                        <div className="yt-calendar-bar yt-calendar-bar-a" style={{ transform: `scaleX(${revealed ? calendarBarScale(a, maxCount) : 0})` }} title={`Channel A: ${a}`} />
                        <div className="yt-calendar-bar yt-calendar-bar-b" style={{ transform: `scaleX(${revealed ? calendarBarScale(b, maxCount) : 0})` }} title={`Channel B: ${b}`} />
                    </div>
                </div>;
            })}
            <div className="yt-calendar-legend"><span className="yt-calendar-bar-a" /> Channel A ({calendar.data.channel_a.sample_size} uploads)<span className="yt-calendar-bar-b" /> Channel B ({calendar.data.channel_b.sample_size} uploads)</div>
        </div>}
    </Panel>;
}

function NetworkGraph({ data }) {
    const nodes = data.nodes || [];
    if (nodes.length === 0) return <p className="yt-note">No connected channels found for this topic.</p>;

    const size = 340;
    const center = size / 2;
    const radius = size / 2 - 46;
    const centralIds = new Set((data.most_central || []).map((c) => c.channel_id));

    const positioned = nodes.map((node, i) => {
        const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
        return { ...node, x: center + radius * Math.cos(angle), y: center + radius * Math.sin(angle) };
    });
    const positionById = Object.fromEntries(positioned.map((n) => [n.channel_id, n]));

    return <div className="yt-chart">
        <svg viewBox={`0 0 ${size} ${size}`} width="100%" height={size} role="img" aria-label="Creator network graph">
            {(data.edges || []).map((edge, i) => {
                const a = positionById[edge.source];
                const b = positionById[edge.target];
                if (!a || !b) return null;
                return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--yt-border-strong)" strokeWidth="1" opacity="0.5" />;
            })}
            {positioned.map((node) => (
                <g key={node.channel_id}>
                    <circle cx={node.x} cy={node.y} r={centralIds.has(node.channel_id) ? 9 : 6} fill={centralIds.has(node.channel_id) ? "var(--yt-accent)" : "var(--yt-text-dim)"} />
                    <text x={node.x} y={node.y - 12} textAnchor="middle" fontSize="9" fill="var(--yt-text-muted)">
                        {node.title.length > 16 ? node.title.slice(0, 15) + "…" : node.title}
                    </text>
                </g>
            ))}
        </svg>
        <p className="yt-note">Larger blue dots = most central channels (PageRank). Lines connect channels whose recent titles share keywords.</p>
    </div>;
}

function CreatorNetworkPanel() {
    const [topic, setTopic] = useState("");
    const network = useAsync();

    return <Panel title="Creator Network (Echo-Chamber Research)">
        <p className="yt-note">Maps which channels cluster together around a topic in your fetched dataset - not YouTube's private recommender.</p>
        <div className="yt-form-row">
            <Field label="Topic" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="AI coding agents" />
            <button onClick={() => network.run(() => getCreatorNetwork(topic))} disabled={network.loading || !topic}>Build network</button>
        </div>
        {network.loading && <Loader label="Building creator network" />}
        {network.error && <p className="yt-error">{network.error}</p>}
        {network.data && <>
            <NetworkGraph data={network.data} />
            {network.data.communities?.length > 0 && <div>
                <p className="yt-note"><strong>Communities detected</strong></p>
                {network.data.communities.map((community, i) => <p className="yt-note" key={i}>
                    Cluster {i + 1}: {community.map((c) => c.title).join(", ")}
                </p>)}
            </div>}
        </>}
    </Panel>;
}

function TopicIntelligencePanel() {
    const [query, setQuery] = useState("");
    const [competitors, setCompetitors] = useState("");
    const topic = useAsync();
    const upcoming = useAsync();

    return <Panel title="Topic Intelligence (Product / Movie / Event)">
        <p className="yt-note">Aggregate sentiment, praised/criticised aspects, purchase intent and competitor mentions across many videos matching a topic.</p>
        <div className="yt-form-row">
            <Field label="Topic, product or movie name" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="iPhone 17 review" />
            <Field label="Competitor names (optional, comma-separated)" value={competitors} onChange={(e) => setCompetitors(e.target.value)} placeholder="Samsung, Pixel" />
        </div>
        <div className="yt-form-row">
            <button onClick={() => topic.run(() => getTopicIntelligence(query, competitors))} disabled={topic.loading || !query}>Analyse topic</button>
            <button onClick={() => upcoming.run(() => getUpcoming(query))} disabled={upcoming.loading || !query}>Find upcoming premieres</button>
        </div>
        {upcoming.loading && <Loader label="Searching for upcoming premieres" />}
        {upcoming.error && <p className="yt-error">{upcoming.error}</p>}
        {upcoming.data?.items?.length > 0 && <ul className="yt-list">
            {upcoming.data.items.map((item) => <li key={item.id.videoId}>{item.snippet.title} — {item.snippet.channelTitle}</li>)}
        </ul>}
        {upcoming.data?.items?.length === 0 && <p className="yt-note">No upcoming premieres found for this topic.</p>}
        {topic.loading && <Loader label="Collecting videos and comments" />}
        {topic.error && <p className="yt-error">{topic.error}</p>}
        {topic.data && <div className="yt-card">
            <StatRow items={[
                ["Videos analyzed", topic.data.videos_analyzed],
                ["Comments analyzed", topic.data.comments_analyzed],
                ["Overall positive", `${topic.data.overall_sentiment.overall_positive_pct}%`],
            ]} />
            {topic.data.most_praised_aspects?.length > 0 && <p className="yt-note">Most praised: {topic.data.most_praised_aspects.join(", ")}</p>}
            {topic.data.most_criticised_aspects?.length > 0 && <p className="yt-note">Most criticised: {topic.data.most_criticised_aspects.join(", ")}</p>}
            <StatRow items={[
                ["Purchase intent (high)", `${topic.data.purchase_intent.high_pct}%`],
                ["Purchase intent (low)", `${topic.data.purchase_intent.low_pct}%`],
                ["Anticipation signals", `${topic.data.anticipation_pct}%`],
            ]} />
            {Object.keys(topic.data.competitor_mentions || {}).length > 0 && <div className="yt-emotions">
                {Object.entries(topic.data.competitor_mentions).map(([name, count]) => <span className="yt-badge" key={name}>{name}: {count}</span>)}
            </div>}
        </div>}
    </Panel>;
}

function SemanticSearchPanel() {
    const [query, setQuery] = useState("");
    const search = useAsync();

    return <Panel title="Semantic Search (lite)">
        <p className="yt-note">Re-ranks YouTube's own search results by TF-IDF text similarity to your full query - meaning-aware, not real embeddings.</p>
        <div className="yt-form-row">
            <Field label="Describe what you're looking for" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="videos explaining why neural networks overfit" />
            <button onClick={() => search.run(() => semanticSearch(query))} disabled={search.loading || !query}>Search</button>
        </div>
        {search.loading && <Loader label="Ranking by similarity" />}
        {search.error && <p className="yt-error">{search.error}</p>}
        {search.data?.items?.map((item) => <div className="yt-card yt-card-row" key={item.id.videoId}>
            <img className="yt-thumb" src={item.snippet.thumbnails?.default?.url} alt="" />
            <div><strong>{item.snippet.title}</strong><span className="yt-muted">{item.snippet.channelTitle} · similarity {item.semantic_similarity}</span></div>
        </div>)}
    </Panel>;
}

// ----------------------------------------------------------------- Analyse

function AnalyseTab({ initial }) {
    const [videoInput, setVideoInput] = useState(initial?.videoInput || "");
    const video = useAsync();
    const thumb = useAsync();
    const misleading = useAsync();
    const botRisk = useAsync();

    const [playlistInput, setPlaylistInput] = useState("");
    const playlist = useAsync();

    const [brandChannelId, setBrandChannelId] = useState("");
    const brandSafety = useAsync();

    const [auditChannelId, setAuditChannelId] = useState(initial?.auditChannelId || "");
    const audit = useAsync();

    const run = () => {
        const id = extractVideoId(videoInput);
        video.run(() => analyzeVideo(id));
    };

    return <div className="yt-grid-2">
        <Panel title="Video Intelligence">
            <div className="yt-form-row">
                <Field label="Video ID or URL" value={videoInput} onChange={(e) => setVideoInput(e.target.value)} placeholder="https://youtube.com/watch?v=..." />
            </div>
            <div className="yt-form-row">
                <button onClick={run} disabled={video.loading || !videoInput}>Analyse</button>
                <button onClick={() => thumb.run(() => analyzeThumbnail(extractVideoId(videoInput)))} disabled={thumb.loading || !videoInput}>Check thumbnail</button>
                <button onClick={() => misleading.run(() => analyzeMisleading(extractVideoId(videoInput)))} disabled={misleading.loading || !videoInput}>Check misleading risk</button>
                <button onClick={() => botRisk.run(() => analyzeBotRisk(extractVideoId(videoInput)))} disabled={botRisk.loading || !videoInput}>Check engagement risk</button>
            </div>
            {video.loading && <Loader label="Analysing video and comments" />}
            {video.error && <p className="yt-error">{video.error}</p>}
            {video.data && <div className="yt-card">
                <div className="yt-card-head">
                    {video.data.video.thumbnail && <img className="yt-thumb" src={video.data.video.thumbnail} alt="" />}
                    <div><strong>{video.data.video.title}</strong><span className="yt-muted">{video.data.video.channel_title}</span></div>
                </div>
                <StatRow items={[
                    ["Views", video.data.engagement.views.toLocaleString()],
                    ["Likes", video.data.engagement.likes.toLocaleString()],
                    ["Comments", video.data.engagement.comments.toLocaleString()],
                    ["Engagement rate", `${video.data.engagement.engagement_rate_pct}%`],
                    ["Virality score", `${video.data.virality.virality_score}/100`],
                ]} />
                <p className="yt-note">{video.data.virality.classification} · projected 7d views {video.data.virality.projected_views_7d_range[0].toLocaleString()}–{video.data.virality.projected_views_7d_range[1].toLocaleString()}</p>

                {video.data.comment_sentiment?.sample_size > 0 && <div className="yt-sentiment">
                    <StatRow items={[
                        ["Positive comments", `${video.data.comment_sentiment.overall_positive_pct}%`],
                        ["Toxicity", `${video.data.comment_sentiment.toxicity_pct}%`],
                        ["Sample size", video.data.comment_sentiment.sample_size],
                    ]} />
                    {Object.keys(video.data.comment_sentiment.dominant_emotions).length > 0 && <div className="yt-emotions">
                        {Object.entries(video.data.comment_sentiment.dominant_emotions).map(([emotion, pct]) => <span className="yt-badge" key={emotion}>{emotion} {pct}%</span>)}
                    </div>}
                    {video.data.comment_sentiment.representative_comments.map((c) => <blockquote className="yt-quote" key={c.type}><span>{c.type.replace("_", " ")}</span>{c.text}</blockquote>)}
                </div>}

                {video.data.aspects && Object.keys(video.data.aspects).length > 0 && <div>
                    <p className="yt-note"><strong>Aspect breakdown</strong></p>
                    {Object.entries(video.data.aspects).map(([aspect, a]) => <div className="yt-aspect-row" key={aspect}>
                        <span>{aspect}</span>
                        <span className="yt-badge">{a.label} ({a.mentions} mentions)</span>
                    </div>)}
                </div>}

                {video.data.topics && video.data.topics.length > 0 && <div>
                    <p className="yt-note"><strong>What people are talking about</strong></p>
                    <ul className="yt-list">
                        {video.data.topics.map((t) => <li key={t.label}>
                            <strong>{t.label}</strong> — {t.comment_count} comments
                            <span className="yt-muted"> · “{t.sample_comment}”</span>
                        </li>)}
                    </ul>
                </div>}
            </div>}

            {thumb.loading && <Loader label="Scoring thumbnail" />}
            {thumb.error && <p className="yt-error">{thumb.error}</p>}
            {thumb.data && <div className="yt-card">
                <div className="yt-card-head"><strong>Thumbnail score</strong><span className="yt-badge">{thumb.data.score}/100</span></div>
                <StatRow items={[["Resolution", thumb.data.resolution], ["Brightness", thumb.data.brightness], ["Contrast", thumb.data.contrast], ["Faces detected", thumb.data.faces_detected ?? "n/a"]]} />
                {thumb.data.issues.length > 0 ? <ul className="yt-list">{thumb.data.issues.map((i) => <li key={i}>{i}</li>)}</ul> : <p className="yt-note">No issues detected.</p>}
                <p className="yt-note">{thumb.data.note}</p>
            </div>}

            {misleading.loading && <Loader label="Checking title/thumbnail accuracy" />}
            {misleading.error && <p className="yt-error">{misleading.error}</p>}
            {misleading.data && <div className="yt-card">
                <div className="yt-card-head"><strong>Misleading risk</strong><span className="yt-badge">{misleading.data.misleading_score}/100</span></div>
                <p className="yt-note">{misleading.data.verdict}</p>
                <StatRow items={[
                    ["Title/description overlap", `${misleading.data.title_description_overlap_pct}%`],
                    ["Clickbait risk", misleading.data.title_clickbait_risk],
                    ["Comments flagging it", `${misleading.data.comments_flagging_misleading_pct}%`],
                ]} />
            </div>}

            {botRisk.loading && <Loader label="Scanning comment patterns" />}
            {botRisk.error && <p className="yt-error">{botRisk.error}</p>}
            {botRisk.data && <div className="yt-card">
                <div className="yt-card-head">
                    <strong>Fake-engagement risk</strong>
                    <span className={`yt-badge ${botRisk.data.risk_level === "high" ? "yt-badge-alert" : ""}`}>{botRisk.data.risk_level} ({botRisk.data.risk_score}/100)</span>
                </div>
                {botRisk.data.patterns.length > 0 ? <ul className="yt-list">{botRisk.data.patterns.map((p) => <li key={p}>{p}</li>)}</ul> : <p className="yt-note">No suspicious patterns detected in this sample.</p>}
                <p className="yt-note">{botRisk.data.note}</p>
            </div>}
        </Panel>

        <div>
            <Panel title="Playlist Intelligence">
                <div className="yt-form-row">
                    <Field label="Playlist ID" value={playlistInput} onChange={(e) => setPlaylistInput(e.target.value)} placeholder="PL... or UU..." />
                    <button onClick={() => playlist.run(() => analyzePlaylist(playlistInput))} disabled={playlist.loading || !playlistInput}>Analyse playlist</button>
                </div>
                {playlist.loading && <Loader label="Analysing playlist" />}
                {playlist.error && <p className="yt-error">{playlist.error}</p>}
                {playlist.data && <div className="yt-card">
                    <StatRow items={[
                        ["Videos", playlist.data.video_count],
                        ["Total views", playlist.data.total_views?.toLocaleString()],
                        ["Avg views", playlist.data.avg_views?.toLocaleString()],
                        ["Consistency", `${playlist.data.consistency_pct}%`],
                    ]} />
                    {playlist.data.best_video && <p className="yt-note">Best: {playlist.data.best_video.title} ({playlist.data.best_video.views?.toLocaleString()} views)</p>}
                    {playlist.data.weakest_video && <p className="yt-note">Weakest: {playlist.data.weakest_video.title} ({playlist.data.weakest_video.views?.toLocaleString()} views)</p>}
                </div>}
            </Panel>

            <Panel title="Brand Safety Score">
                <div className="yt-form-row">
                    <Field label="Channel ID" value={brandChannelId} onChange={(e) => setBrandChannelId(e.target.value)} placeholder="UC..." />
                    <button onClick={() => brandSafety.run(() => analyzeBrandSafety(extractChannelId(brandChannelId)))} disabled={brandSafety.loading || !brandChannelId}>Score channel</button>
                </div>
                {brandSafety.loading && <Loader label="Sampling recent videos and comments" />}
                {brandSafety.error && <p className="yt-error">{brandSafety.error}</p>}
                {brandSafety.data && <div className="yt-card">
                    <div className="yt-card-head"><strong>Brand safety</strong><span className="yt-badge">{brandSafety.data.brand_safety_score}/100</span></div>
                    {brandSafety.data.strengths.length > 0 && <p className="yt-note">Strengths: {brandSafety.data.strengths.join(", ")}</p>}
                    {brandSafety.data.risks.length > 0 && <p className="yt-note">Risks: {brandSafety.data.risks.join(", ")}</p>}
                </div>}
            </Panel>

            <Panel title="Channel Audit (Portfolio Evaluator)">
                <p className="yt-note">Combines brand safety, title quality, upload consistency and growth into one score with prioritized recommendations.</p>
                <div className="yt-form-row">
                    <Field label="Channel ID" value={auditChannelId} onChange={(e) => setAuditChannelId(e.target.value)} placeholder="UC..." />
                    <button onClick={() => audit.run(() => analyzeChannelAudit(extractChannelId(auditChannelId)))} disabled={audit.loading || !auditChannelId}>Run audit</button>
                </div>
                {audit.loading && <Loader label="Auditing channel" />}
                {audit.error && <p className="yt-error">{audit.error}</p>}
                {audit.data && <div className="yt-card">
                    <div className="yt-card-head"><strong>Channel Intelligence Score</strong><span className="yt-badge">{audit.data.channel_intelligence_score}/100</span></div>
                    <StatRow items={[
                        ["Brand safety", audit.data.components.brand_safety_score],
                        ["Avg title score", audit.data.components.avg_title_score],
                        ["Upload consistency", audit.data.components.upload_consistency],
                    ]} />
                    <p className="yt-note"><strong>Top recommendations</strong></p>
                    <ul className="yt-list">{audit.data.recommendations.map((r) => <li key={r}>{r}</li>)}</ul>
                    {audit.data.channel_sections?.filter((s) => s.type !== "channelsectiontypeundefined").length > 0 && <>
                        <p className="yt-note"><strong>Channel sections</strong></p>
                        <div className="yt-emotions">
                            {audit.data.channel_sections.filter((s) => s.type !== "channelsectiontypeundefined").map((s, i) => (
                                <span className="yt-badge yt-badge-muted" key={i}>{s.type.replace(/([a-z])([A-Z])/g, "$1 $2")}</span>
                            ))}
                        </div>
                    </>}
                </div>}
            </Panel>
        </div>
    </div>;
}

// ----------------------------------------------------------------- Predict

function PredictTab() {
    const [videoInput, setVideoInput] = useState("");
    const virality = useAsync();
    const viralityMl = useAsync();
    const [channelId, setChannelId] = useState("");
    const growth = useAsync();
    const growthMl = useAsync();

    return <div className="yt-grid-2">
        <Panel title="Virality Prediction">
            <div className="yt-form-row">
                <Field label="Video ID or URL" value={videoInput} onChange={(e) => setVideoInput(e.target.value)} />
            </div>
            <div className="yt-form-row">
                <button onClick={() => virality.run(() => predictVirality(extractVideoId(videoInput)))} disabled={virality.loading || !videoInput}>Predict (heuristic)</button>
                <button onClick={() => viralityMl.run(() => predictViralityMl(extractVideoId(videoInput)))} disabled={viralityMl.loading || !videoInput}>Predict (trained model)</button>
            </div>
            {virality.loading && <Loader label="Scoring virality" />}
            {virality.error && <p className="yt-error">{virality.error}</p>}
            {virality.data && <div className="yt-card">
                <div className="yt-card-head"><strong>Virality score</strong><span className="yt-badge">{virality.data.virality_score}/100</span></div>
                <p className="yt-note">{virality.data.classification}</p>
                <p className="yt-note">Projected 7-day views: {virality.data.projected_views_7d_range[0].toLocaleString()} – {virality.data.projected_views_7d_range[1].toLocaleString()}</p>
            </div>}

            {viralityMl.loading && <Loader label="Training on your tracked-video history" />}
            {viralityMl.error && <p className="yt-error">{viralityMl.error}</p>}
            {viralityMl.data && <div className="yt-card">
                {viralityMl.data.trained ? <>
                    <div className="yt-card-head"><strong>Trained model prediction</strong><span className="yt-badge">{viralityMl.data.predicted_virality_score}/100</span></div>
                    <p className="yt-note">Trained on {viralityMl.data.sample_size} tracked videos · in-sample R² {viralityMl.data.in_sample_r2}</p>
                    <p className="yt-note">{viralityMl.data.note}</p>
                    <p className="yt-note"><strong>Top feature:</strong> {Object.entries(viralityMl.data.feature_importances)[0]?.[0]}</p>
                </> : <>
                    <p className="yt-error">{viralityMl.data.note}</p>
                    <p className="yt-note">Falling back to heuristic: virality score {viralityMl.data.heuristic_result.virality_score}/100</p>
                </>}
            </div>}
        </Panel>

        <Panel title="Channel Growth Forecast">
            <div className="yt-form-row">
                <Field label="Channel ID" value={channelId} onChange={(e) => setChannelId(e.target.value)} placeholder="UC..." />
            </div>
            <div className="yt-form-row">
                <button onClick={() => growth.run(() => predictChannelGrowth(extractChannelId(channelId)))} disabled={growth.loading || !channelId}>Forecast (heuristic)</button>
                <button onClick={() => growthMl.run(() => predictChannelGrowthMl(extractChannelId(channelId)))} disabled={growthMl.loading || !channelId}>Forecast (ARIMA, needs tracking)</button>
            </div>
            {growth.loading && <Loader label="Forecasting growth" />}
            {growth.error && <p className="yt-error">{growth.error}</p>}
            {growth.data && <div className="yt-card">
                <StatRow items={[
                    ["Current subscribers", growth.data.current_subscribers.toLocaleString()],
                    ["30d estimate (low)", growth.data.estimated_subscribers_30d[0].toLocaleString()],
                    ["30d estimate (high)", growth.data.estimated_subscribers_30d[1].toLocaleString()],
                ]} />
                <p className="yt-note">{growth.data.basis}</p>
            </div>}

            {growthMl.loading && <Loader label="Fitting ARIMA on snapshot history" />}
            {growthMl.error && <p className="yt-error">{growthMl.error}</p>}
            {growthMl.data && <div className="yt-card">
                {growthMl.data.method === "arima" ? <>
                    <div className="yt-card-head"><strong>ARIMA forecast</strong><span className="yt-badge">{growthMl.data.estimated_subscribers.toLocaleString()}</span></div>
                    <p className="yt-note">Range: {growthMl.data.estimated_range[0].toLocaleString()} – {growthMl.data.estimated_range[1].toLocaleString()}, based on {growthMl.data.sample_size} snapshots.</p>
                </> : <>
                    <p className="yt-error">Not enough snapshot history ({growthMl.data.sample_size}/{growthMl.data.min_required} required) - track this channel and let snapshots build up.</p>
                    {growthMl.data.heuristic_result && <p className="yt-note">Falling back to heuristic: {growthMl.data.heuristic_result.estimated_subscribers_30d[0].toLocaleString()}–{growthMl.data.heuristic_result.estimated_subscribers_30d[1].toLocaleString()}</p>}
                </>}
            </div>}
        </Panel>
    </div>;
}

// ------------------------------------------------------------------ Create

function CreateTab() {
    const [topic, setTopic] = useState("");
    const [style, setStyle] = useState("educational");
    const titles = useAsync();

    const [channelId, setChannelId] = useState("");
    const timing = useAsync();
    const insights = useAsync();

    return <div className="yt-grid-2">
        <Panel title="Title Generator">
            <div className="yt-form-row">
                <Field label="Topic" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Premier League tactics" />
                <label className="yt-field"><span>Style</span>
                    <select value={style} onChange={(e) => setStyle(e.target.value)}>
                        <option value="educational">Educational</option>
                        <option value="engaging">Engaging</option>
                        <option value="news">News</option>
                    </select>
                </label>
                <button onClick={() => titles.run(() => createTitles(topic, style))} disabled={titles.loading || !topic}>Generate</button>
            </div>
            {titles.loading && <Loader label="Generating titles" />}
            {titles.error && <p className="yt-error">{titles.error}</p>}
            {titles.data?.variants?.map((v) => <div className="yt-card yt-title-card" key={v.title}>
                <strong>{v.title}</strong>
                <StatRow items={[["Score", `${v.score}/100`], ["CTR class", v.predicted_ctr_class], ["Clickbait risk", v.clickbait_risk]]} />
            </div>)}
        </Panel>

        <div>
            <Panel title="Best Upload Timing">
                <div className="yt-form-row">
                    <Field label="Channel ID" value={channelId} onChange={(e) => setChannelId(e.target.value)} placeholder="UC..." />
                    <button onClick={() => timing.run(() => getUploadTiming(extractChannelId(channelId)))} disabled={timing.loading || !channelId}>Analyse uploads</button>
                </div>
                {timing.loading && <Loader label="Analysing upload history" />}
                {timing.error && <p className="yt-error">{timing.error}</p>}
                {timing.data && <div className="yt-card">
                    <StatRow items={[["Best weekday", timing.data.best_weekday || "n/a"], ["Best hour (UTC)", timing.data.best_hour_utc ?? "n/a"], ["Sample size", timing.data.sample_size]]} />
                    {timing.data.avg_views_by_weekday && <ul className="yt-list">
                        {Object.entries(timing.data.avg_views_by_weekday).map(([day, views]) => <li key={day}>{day}: {Math.round(views).toLocaleString()} avg views</li>)}
                    </ul>}
                </div>}
            </Panel>

            <Panel title="Personalized Title Insights">
                <p className="yt-note">Correlates title patterns with how your own tracked videos actually performed.</p>
                <div className="yt-form-row">
                    <button onClick={() => insights.run(() => getPersonalizedInsights())} disabled={insights.loading}>Compute insights</button>
                </div>
                {insights.loading && <Loader label="Correlating title patterns with performance" />}
                {insights.error && <p className="yt-error">{insights.error}</p>}
                {insights.data && <div className="yt-card">
                    <p className="yt-note">Based on {insights.data.sample_size} tracked video(s).</p>
                    {insights.data.note && <p className="yt-note">{insights.data.note}</p>}
                    <ul className="yt-list">{insights.data.insights?.map((line) => <li key={line}>{line}</li>)}</ul>
                </div>}
            </Panel>
        </div>
    </div>;
}

// ----------------------------------------------------------------- Monitor

function MonitorTab() {
    const [videoInput, setVideoInput] = useState("");
    const [multilingual, setMultilingual] = useState(false);
    const sentiment = useAsync();
    const [channelId, setChannelId] = useState("");
    const anomalies = useAsync();
    const [liveVideoInput, setLiveVideoInput] = useState("");
    const liveChat = useAsync();
    const [liveTopic, setLiveTopic] = useState("");
    const liveNow = useAsync();
    const live = useLiveChatMonitor();

    return <div className="yt-grid-2">
        <Panel title="Live Sentiment Snapshot">
            <p className="yt-note">Poll-based comment sentiment — re-run to refresh.</p>
            <div className="yt-form-row">
                <Field label="Video ID or URL" value={videoInput} onChange={(e) => setVideoInput(e.target.value)} />
                <label className="yt-field yt-checkbox">
                    <input type="checkbox" checked={multilingual} onChange={(e) => setMultilingual(e.target.checked)} />
                    <span>Detect + translate non-English comments</span>
                </label>
                <button onClick={() => sentiment.run(() => monitorSentiment(extractVideoId(videoInput), 50, multilingual))} disabled={sentiment.loading || !videoInput}>Snapshot</button>
            </div>
            {sentiment.loading && <Loader label="Reading recent comments" />}
            {sentiment.error && <p className="yt-error">{sentiment.error}</p>}
            {sentiment.data && <div className="yt-card">
                <StatRow items={[
                    ["Positive", `${sentiment.data.overall_positive_pct}%`],
                    ["Toxicity", `${sentiment.data.toxicity_pct}%`],
                    ["Sample size", sentiment.data.sample_size],
                ]} />
                {sentiment.data.toxicity_pct > 10 && <p className="yt-error">Toxicity alert: elevated hostile comment rate.</p>}
                {sentiment.data.language_breakdown && <div className="yt-emotions">
                    {Object.entries(sentiment.data.language_breakdown).map(([lang, info]) => <span className="yt-badge" key={lang}>{lang} {info.pct}%</span>)}
                </div>}
            </div>}
        </Panel>

        <Panel title="Performance Anomalies">
            <div className="yt-form-row">
                <Field label="Channel ID" value={channelId} onChange={(e) => setChannelId(e.target.value)} placeholder="UC..." />
                <button onClick={() => anomalies.run(() => monitorAnomalies(extractChannelId(channelId)))} disabled={anomalies.loading || !channelId}>Scan uploads</button>
            </div>
            {anomalies.loading && <Loader label="Scanning recent uploads" />}
            {anomalies.error && <p className="yt-error">{anomalies.error}</p>}
            {anomalies.data && (anomalies.data.anomalies.length > 0 ? <ul className="yt-list">
                {anomalies.data.anomalies.map((a) => <li key={a.video_id}><strong><DirectionIcon direction={a.direction} /> {a.title}</strong> — {a.views_per_day.toLocaleString()} views/day (z={a.z_score})</li>)}
            </ul> : <p className="yt-note">No statistical outliers in recent uploads.</p>)}
        </Panel>

        <Panel title="Live Chat Sentiment">
            <p className="yt-note">Only works while the video is actively live-streaming. Re-run to refresh.</p>
            <div className="yt-form-row">
                <Field label="Find what's live now" value={liveTopic} onChange={(e) => setLiveTopic(e.target.value)} placeholder="Premier League" />
                <button onClick={() => liveNow.run(() => getLiveNow(liveTopic))} disabled={liveNow.loading || !liveTopic}>Find live streams</button>
            </div>
            {liveNow.loading && <Loader label="Searching for live streams" />}
            {liveNow.error && <p className="yt-error">{liveNow.error}</p>}
            {liveNow.data?.items?.length > 0 && <ul className="yt-list">
                {liveNow.data.items.map((item) => <li key={item.id.videoId}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setLiveVideoInput(item.id.videoId); }}>{item.snippet.title}</a> — {item.snippet.channelTitle}
                </li>)}
            </ul>}
            {liveNow.data?.items?.length === 0 && <p className="yt-note">Nothing live for this topic right now.</p>}

            <div className="yt-form-row">
                <Field label="Live video ID or URL" value={liveVideoInput} onChange={(e) => setLiveVideoInput(e.target.value)} />
                <button onClick={() => liveChat.run(() => monitorLiveChat(extractVideoId(liveVideoInput)))} disabled={liveChat.loading || !liveVideoInput}>Check live chat</button>
                <button onClick={() => live.start(extractVideoId(liveVideoInput))} disabled={!liveVideoInput || live.status === "connecting" || live.status === "live"}>
                    {live.status === "live" ? "Live" : live.status === "connecting" ? "Connecting…" : "Go live"}
                </button>
                {(live.status === "live" || live.status === "connecting") && <button type="button" onClick={live.stop}>Stop</button>}
            </div>
            {liveChat.loading && <Loader label="Reading live chat" />}
            {liveChat.error && <p className="yt-error">{liveChat.error}</p>}
            {liveChat.data && <div className="yt-card">
                <StatRow items={[
                    ["Messages sampled", liveChat.data.message_count],
                    ["Positive", `${liveChat.data.sentiment.overall_positive_pct}%`],
                    ["Toxicity", `${liveChat.data.sentiment.toxicity_pct}%`],
                ]} />
                {liveChat.data.toxicity_alert && <p className="yt-error">Toxicity alert: elevated hostile chat rate.</p>}
                {liveChat.data.message_count === 0 && <p className="yt-note">No chat messages in this poll window — try again shortly.</p>}
            </div>}

            {live.status === "connecting" && <Loader label="Connecting to live chat" />}
            {(live.status === "live" || (live.status === "ended" && live.latest)) && live.latest && <div className="yt-card">
                <StatRow key={live.latest.elapsed_seconds} items={[
                    ["Messages/min", live.latest.messages_per_min],
                    ["Positive", live.latest.sentiment ? `${live.latest.sentiment.overall_positive_pct}%` : "—"],
                    ["Toxicity", live.latest.sentiment ? `${live.latest.sentiment.toxicity_pct}%` : "—"],
                ]} />
                {live.latest.toxicity_alert && <p className="yt-error">Toxicity alert: elevated hostile chat rate.</p>}
                <LiveVelocityChart ticks={live.ticks} />
                <p className="yt-note">
                    {Math.max(live.latest.session_limit_seconds - live.latest.elapsed_seconds, 0)}s left this session · {live.latest.quota.remaining}/{live.latest.quota.daily_budget} YouTube quota units left today
                </p>
            </div>}
            {live.status === "ended" && <p className="yt-note">{LIVE_CHAT_END_MESSAGES[live.endReason] || "Live session ended."}</p>}
        </Panel>
    </div>;
}

// --------------------------------------------------------------- Recommend

function RecommendTab() {
    const [videoInput, setVideoInput] = useState("");
    const similar = useAsync();

    const [ownId, setOwnId] = useMyChannel();
    const [competitorIds, setCompetitorIds] = useState("");
    const ideas = useAsync();

    return <div className="yt-grid-2">
        <Panel title="Similar Videos">
            <div className="yt-form-row">
                <Field label="Video ID or URL" value={videoInput} onChange={(e) => setVideoInput(e.target.value)} />
                <button onClick={() => similar.run(() => recommendSimilar(extractVideoId(videoInput)))} disabled={similar.loading || !videoInput}>Find similar</button>
            </div>
            {similar.loading && <Loader label="Searching for similar videos" />}
            {similar.error && <p className="yt-error">{similar.error}</p>}
            {similar.data?.items?.map((item) => <div className="yt-card yt-card-row" key={item.id.videoId}>
                <img className="yt-thumb" src={item.snippet.thumbnails?.default?.url} alt="" />
                <div><strong>{item.snippet.title}</strong><span className="yt-muted">{item.snippet.channelTitle}</span></div>
            </div>)}
        </Panel>

        <Panel title="Next Video Ideas">
            <div className="yt-form-row">
                <Field label="Your channel ID" value={ownId} onChange={(e) => setOwnId(e.target.value)} placeholder="UC..." />
                <Field label="Competitor channel IDs" value={competitorIds} onChange={(e) => setCompetitorIds(e.target.value)} placeholder="UC..., UC..." />
                <button onClick={() => ideas.run(() => recommendNextVideoIdeas(extractChannelId(ownId), extractChannelIdsCsv(competitorIds)))} disabled={ideas.loading || !ownId || !competitorIds}>Suggest</button>
            </div>
            {ideas.loading && <Loader label="Building content ideas" />}
            {ideas.error && <p className="yt-error">{ideas.error}</p>}
            {ideas.data?.ideas?.map((idea) => <div className="yt-card" key={idea.topic}>
                <strong>{idea.topic}</strong>
                <p className="yt-note">{idea.why}</p>
                <ul className="yt-list">{idea.suggested_titles.map((t) => <li key={t.title}>{t.title}</li>)}</ul>
            </div>)}
        </Panel>
    </div>;
}

// ----------------------------------------------------------------- Tracking

function HistoryChart({ data, dataKey, label }) {
    if (!data || data.length < 2) {
        return <p className="yt-note">Not enough history yet — snapshots build up over time as the background poller runs (or trigger one manually on the backend).</p>;
    }
    const points = data.map((d) => ({ date: new Date(d.captured_at).toLocaleDateString(), value: d[dataKey] }));
    const gridColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-border").trim() || "#29466f";
    const textColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-text-dim").trim() || "#7690b6";
    const surfaceColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-surface").trim() || "#0d1627";
    const primaryColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-text-primary").trim() || "#f8fafc";
    const accentColor = getComputedStyle(document.documentElement).getPropertyValue("--yt-accent").trim() || "#a3341f";
    return <div className="yt-chart">
        <ResponsiveContainer width="100%" height={180}>
            <LineChart data={points}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="date" stroke={textColor} fontSize={11} />
                <YAxis stroke={textColor} fontSize={11} />
                <Tooltip contentStyle={{ background: surfaceColor, border: `1px solid ${gridColor}`, borderRadius: 8, color: primaryColor }} />
                <Line type="monotone" dataKey="value" name={label} stroke={accentColor} strokeWidth={2} dot={false} />
            </LineChart>
        </ResponsiveContainer>
    </div>;
}

function TrackedChannelsPanel() {
    const [channelId, setChannelId] = useState("");
    const [label, setLabel] = useState("");
    const [tracked, setTracked] = useState([]);
    const [selected, setSelected] = useState(null);
    const history = useAsync();

    const refresh = () => listTrackedChannels().then((d) => setTracked(d.items)).catch(() => setTracked([]));
    useEffect(() => { refresh(); }, []);

    const add = async () => {
        await trackChannel(extractChannelId(channelId), label || null);
        setChannelId(""); setLabel("");
        refresh();
    };

    const remove = async (id) => {
        await untrackChannel(id);
        if (selected === id) setSelected(null);
        refresh();
    };

    const view = (row) => {
        setSelected(row.id);
        history.run(() => getChannelHistory(row.channel_id));
    };

    return <Panel title="Tracked Channels">
        <p className="yt-note">Tracked channels are snapshotted periodically by the backend (subscribers, views, avg views/day) so trends show up over time instead of only live data.</p>
        <div className="yt-form-row">
            <Field label="Channel ID" value={channelId} onChange={(e) => setChannelId(e.target.value)} placeholder="UC..." />
            <Field label="Label (optional)" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Manchester United" />
            <button onClick={add} disabled={!channelId}>Track</button>
        </div>
        {tracked.length === 0 ? <p className="yt-note">No channels tracked yet.</p> : <ul className="yt-list">
            {tracked.map((row) => <li key={row.id}>
                <strong>{row.label || row.channel_id}</strong> ({row.channel_id})
                {" — "}<a href="#" onClick={(e) => { e.preventDefault(); view(row); }}>view history</a>
                {" · "}<a className="yt-export-link" href={channelHistoryCsvUrl(row.channel_id)} target="_blank" rel="noreferrer">export CSV</a>
                {" · "}<a href="#" onClick={(e) => { e.preventDefault(); remove(row.id); }}>remove</a>
            </li>)}
        </ul>}
        {selected && <>
            {history.loading && <Loader label="Loading history" />}
            {history.error && <p className="yt-error">{history.error}</p>}
            {history.data && <HistoryChart data={history.data.items} dataKey="subscribers" label="Subscribers" />}
        </>}
    </Panel>;
}

function TrackedVideosPanel() {
    const [videoInput, setVideoInput] = useState("");
    const [label, setLabel] = useState("");
    const [tracked, setTracked] = useState([]);
    const [selected, setSelected] = useState(null);
    const history = useAsync();

    const refresh = () => listTrackedVideos().then((d) => setTracked(d.items)).catch(() => setTracked([]));
    useEffect(() => { refresh(); }, []);

    const add = async () => {
        await trackVideo(extractVideoId(videoInput), label || null);
        setVideoInput(""); setLabel("");
        refresh();
    };

    const remove = async (id) => {
        await untrackVideo(id);
        if (selected === id) setSelected(null);
        refresh();
    };

    const view = (row) => {
        setSelected(row.id);
        history.run(() => getVideoHistory(row.video_id));
    };

    return <Panel title="Tracked Videos">
        <p className="yt-note">Tracked videos are snapshotted periodically (views, likes, comments, virality score, sentiment).</p>
        <div className="yt-form-row">
            <Field label="Video ID or URL" value={videoInput} onChange={(e) => setVideoInput(e.target.value)} />
            <Field label="Label (optional)" value={label} onChange={(e) => setLabel(e.target.value)} />
            <button onClick={add} disabled={!videoInput}>Track</button>
        </div>
        {tracked.length === 0 ? <p className="yt-note">No videos tracked yet.</p> : <ul className="yt-list">
            {tracked.map((row) => <li key={row.id}>
                <strong>{row.label || row.video_id}</strong> ({row.video_id})
                {" — "}<a href="#" onClick={(e) => { e.preventDefault(); view(row); }}>view history</a>
                {" · "}<a className="yt-export-link" href={videoHistoryCsvUrl(row.video_id)} target="_blank" rel="noreferrer">export CSV</a>
                {" · "}<a href="#" onClick={(e) => { e.preventDefault(); remove(row.id); }}>remove</a>
            </li>)}
        </ul>}
        {selected && <>
            {history.loading && <Loader label="Loading history" />}
            {history.error && <p className="yt-error">{history.error}</p>}
            {history.data && <HistoryChart data={history.data.items} dataKey="views" label="Views" />}
        </>}
    </Panel>;
}

function CreatorAnalyticsPanel() {
    const [status, setStatus] = useState(null);
    const [checkFailed, setCheckFailed] = useState(false);
    const analytics = useAsync();

    const refresh = () => {
        setCheckFailed(false);
        getOAuthStatus().then(setStatus).catch(() => setCheckFailed(true));
    };
    useEffect(() => { refresh(); }, []);

    const connect = async () => {
        const { authorize_url } = await getOAuthAuthorizeUrl();
        window.location.href = authorize_url;
    };

    const disconnect = async () => {
        await disconnectOAuth();
        refresh();
    };

    return <Panel title="Creator Analytics (OAuth)">
        <p className="yt-note">Sign in with your own YouTube account to pull private metrics (watch time, subscriber deltas) unavailable through the public API. Requires GOOGLE_OAUTH_CLIENT_ID/SECRET to be configured on the backend.</p>
        {checkFailed ? (
            <p className="yt-error">Couldn't reach the backend to check the connection. <a href="#" onClick={(e) => { e.preventDefault(); refresh(); }}>Retry</a></p>
        ) : !status ? <Loader label="Checking connection" /> : !status.configured ? (
            <p className="yt-error">OAuth not configured on the backend — add GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET to backend/.env.</p>
        ) : !status.connected ? (
            <button onClick={connect}>Connect YouTube account</button>
        ) : <div className="yt-card">
            <StatRow items={[["Connected as", status.connected_email || "unknown"], ["Channel", status.connected_channel_id || "n/a"]]} />
            <div className="yt-form-row">
                <button onClick={() => analytics.run(() => getOAuthAnalytics(28))} disabled={analytics.loading}>Fetch 28-day analytics</button>
                <button onClick={disconnect}>Disconnect</button>
            </div>
            {analytics.loading && <Loader label="Fetching analytics" />}
            {analytics.error && <p className="yt-error">{analytics.error}</p>}
            {analytics.data && <pre className="yt-json">{JSON.stringify(analytics.data, null, 2)}</pre>}
        </div>}
    </Panel>;
}

function DigestPanel() {
    const digest = useAsync();

    useEffect(() => { digest.run(() => getTrackingDigest()); }, []);

    return <Panel title="Watchlist Digest">
        <div className="yt-form-row">
            <button onClick={() => digest.run(() => getTrackingDigest())} disabled={digest.loading}>Refresh</button>
        </div>
        {digest.loading && <Loader label="Building digest" />}
        {digest.error && <p className="yt-note">Couldn't reach the backend to build a digest yet — hit Refresh once it's up, or track a channel or video below to get started.</p>}
        {digest.data && <>
            {digest.data.channels.length === 0 && digest.data.videos.length === 0 && <p className="yt-note">Nothing tracked yet.</p>}
            {digest.data.channels.map((c) => <div className="yt-card" key={c.channel_id}>
                <div className="yt-card-head"><strong>{c.label || c.channel_id}</strong><span className="yt-muted">channel</span></div>
                <StatRow items={[
                    ["Subscribers", c.latest_subscribers?.toLocaleString() ?? "no snapshot yet"],
                    ["Avg views/day", c.avg_views_per_day_recent?.toLocaleString() ?? "-"],
                    ["Sub change", c.subscriber_change_since_last_snapshot ?? "-"],
                ]} />
            </div>)}
            {digest.data.videos.map((v) => <div className="yt-card" key={v.video_id}>
                <div className="yt-card-head"><strong>{v.label || v.video_id}</strong><span className="yt-muted">video</span></div>
                <StatRow items={[
                    ["Views", v.latest_views?.toLocaleString() ?? "no snapshot yet"],
                    ["Virality", v.virality_score ?? "-"],
                    ["Positive", v.positive_pct != null ? `${v.positive_pct}%` : "-"],
                ]} />
            </div>)}
        </>}
    </Panel>;
}

const CHANNEL_LEADERBOARD_METRICS = [
    ["subscriber_change", "Subscriber change"],
    ["subscribers", "Subscribers"],
    ["avg_views_per_day_recent", "Avg views/day"],
    ["total_views", "Total views"],
];
const VIDEO_LEADERBOARD_METRICS = [
    ["view_change", "View change"],
    ["views", "Views"],
    ["virality_score", "Virality score"],
    ["virality_change", "Virality change"],
    ["positive_pct", "Positive sentiment"],
];

function LeaderboardPanel() {
    const [kind, setKind] = useState("channels");
    const [metric, setMetric] = useState(CHANNEL_LEADERBOARD_METRICS[0][0]);
    const board = useAsync();

    const metrics = kind === "channels" ? CHANNEL_LEADERBOARD_METRICS : VIDEO_LEADERBOARD_METRICS;

    const load = (nextKind, nextMetric) => {
        const fn = nextKind === "channels" ? getChannelLeaderboard : getVideoLeaderboard;
        board.run(() => fn(nextMetric));
    };

    useEffect(() => { load(kind, metric); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const changeKind = (nextKind) => {
        const nextMetric = (nextKind === "channels" ? CHANNEL_LEADERBOARD_METRICS : VIDEO_LEADERBOARD_METRICS)[0][0];
        setKind(nextKind); setMetric(nextMetric);
        load(nextKind, nextMetric);
    };

    const changeMetric = (nextMetric) => {
        setMetric(nextMetric);
        load(kind, nextMetric);
    };

    return <Panel title="Leaderboard">
        <p className="yt-note">Ranked from stored snapshot history — zero additional YouTube quota, however often you re-rank it.</p>
        <div className="yt-form-row">
            <label className="yt-field"><span>Rank</span>
                <select value={kind} onChange={(e) => changeKind(e.target.value)}>
                    <option value="channels">Tracked channels</option>
                    <option value="videos">Tracked videos</option>
                </select>
            </label>
            <label className="yt-field"><span>By</span>
                <select value={metric} onChange={(e) => changeMetric(e.target.value)}>
                    {metrics.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
            </label>
        </div>
        {board.loading && <Loader label="Ranking tracked items" />}
        {board.error && <p className="yt-error">{board.error}</p>}
        {board.data && (board.data.items.length === 0
            ? <p className="yt-note">Nothing ranked yet — track a few {kind} and let at least two snapshots accumulate.</p>
            : <ol className="yt-list yt-list-ranked">
                {board.data.items.map((item, i) => <li key={item.channel_id || item.video_id}>
                    <span className="yt-rank">{i + 1}</span>
                    <strong>{item.label || item.channel_id || item.video_id}</strong>
                    <span className="yt-muted">{typeof item[metric] === "number" ? item[metric].toLocaleString() : "—"}</span>
                </li>)}
            </ol>)}
    </Panel>;
}

function MilestonesPanel() {
    const milestones = useAsync();
    useEffect(() => { milestones.run(() => getTrackingMilestones()); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    return <Panel title="Milestone Alerts">
        <p className="yt-note">Notable jumps found by diffing consecutive snapshots — subscriber milestones crossed, virality or sentiment swings. Zero additional quota.</p>
        <div className="yt-form-row">
            <button onClick={() => milestones.run(() => getTrackingMilestones())} disabled={milestones.loading}>Refresh</button>
        </div>
        {milestones.loading && <Loader label="Scanning snapshot history" />}
        {milestones.error && <p className="yt-error">{milestones.error}</p>}
        {milestones.data && (milestones.data.items.length === 0
            ? <p className="yt-note">No notable swings yet — these show up once tracked items have at least two snapshots apart.</p>
            : <ul className="yt-list">
                {milestones.data.items.map((e, i) => <li key={i}>
                    <strong>{e.label}</strong> — {e.message}
                    <span className="yt-muted"> · {new Date(e.captured_at).toLocaleString()}</span>
                </li>)}
            </ul>)}
    </Panel>;
}

function CompareChannelsPanel() {
    const [tracked, setTracked] = useState([]);
    const [selected, setSelected] = useState([]);
    const compare = useAsync();

    useEffect(() => { listTrackedChannels().then((d) => setTracked(d.items)).catch(() => setTracked([])); }, []);

    const toggle = (channelId) => {
        setSelected((prev) => prev.includes(channelId)
            ? prev.filter((id) => id !== channelId)
            : prev.length < 4 ? [...prev, channelId] : prev);
    };

    const run = () => compare.run(() => compareChannels(selected.join(",")));

    const points = compare.data ? (() => {
        const dateSet = new Set();
        compare.data.series.forEach((s) => s.history.forEach((h) => dateSet.add(new Date(h.captured_at).toLocaleDateString())));
        return [...dateSet].sort().map((date) => {
            const row = { date };
            compare.data.series.forEach((s) => {
                const match = s.history.find((h) => new Date(h.captured_at).toLocaleDateString() === date);
                if (match) row[s.channel_id] = match.subscribers;
            });
            return row;
        });
    })() : [];

    const lineColors = ["--yt-accent", "--yt-success-text", "--yt-warning-text", "--yt-text-dim"];

    return <Panel title="Compare Channels">
        <p className="yt-note">Head-to-head subscriber history for 2-4 tracked channels — reuses history you already have, zero additional quota.</p>
        {tracked.length < 2 ? <p className="yt-note">Track at least 2 channels above to compare them.</p> : <>
            <div className="yt-emotions">
                {tracked.map((t) => <label key={t.channel_id} className="yt-checkbox-chip">
                    <input type="checkbox" checked={selected.includes(t.channel_id)} onChange={() => toggle(t.channel_id)} />
                    <span>{t.label || t.channel_id}</span>
                </label>)}
            </div>
            <div className="yt-form-row">
                <button onClick={run} disabled={selected.length < 2 || compare.loading}>Compare</button>
            </div>
        </>}
        {compare.loading && <Loader label="Loading comparison" />}
        {compare.error && <p className="yt-error">{compare.error}</p>}
        {compare.data && (points.length < 2
            ? <p className="yt-note">Not enough overlapping history yet for these channels.</p>
            : <div className="yt-chart">
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={points}>
                        <CartesianGrid strokeDasharray="3 3" stroke={getComputedStyle(document.documentElement).getPropertyValue("--yt-border").trim()} />
                        <XAxis dataKey="date" stroke={getComputedStyle(document.documentElement).getPropertyValue("--yt-text-dim").trim()} fontSize={11} />
                        <YAxis stroke={getComputedStyle(document.documentElement).getPropertyValue("--yt-text-dim").trim()} fontSize={11} />
                        <Tooltip contentStyle={{
                            background: getComputedStyle(document.documentElement).getPropertyValue("--yt-surface").trim(),
                            border: `1px solid ${getComputedStyle(document.documentElement).getPropertyValue("--yt-border").trim()}`,
                            borderRadius: 8, color: getComputedStyle(document.documentElement).getPropertyValue("--yt-text-primary").trim(),
                        }} />
                        {compare.data.series.map((s, i) => <Line key={s.channel_id} type="monotone" dataKey={s.channel_id} name={s.label}
                            stroke={getComputedStyle(document.documentElement).getPropertyValue(lineColors[i % lineColors.length]).trim()}
                            strokeWidth={2} dot={false} connectNulls />)}
                    </LineChart>
                </ResponsiveContainer>
            </div>)}
    </Panel>;
}

function TrackingTab() {
    return <div className="yt-grid-2">
        <DigestPanel />
        <LeaderboardPanel />
        <MilestonesPanel />
        <CompareChannelsPanel />
        <TrackedChannelsPanel />
        <TrackedVideosPanel />
        <CreatorAnalyticsPanel />
    </div>;
}

function readLandingIntent() {
    try {
        const raw = sessionStorage.getItem("yt-landing-intent");
        if (!raw) return null;
        sessionStorage.removeItem("yt-landing-intent");
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function YoutubeIntel({ theme, onToggleTheme, onNavigate }) {
    const [landingIntent] = useState(readLandingIntent);
    const [tab, setTab] = useState(landingIntent?.tab || "overview");
    const [configured, setConfigured] = useState(true);
    const [quota, setQuota] = useState(null);
    const [oauthNotice, setOauthNotice] = useState(null);
    const tabRefs = useRef({});
    const tabsNavRef = useRef(null);
    const [indicator, setIndicator] = useState({ left: 0, scale: 0 });

    useEffect(() => {
        const el = tabRefs.current[tab];
        const nav = tabsNavRef.current;
        if (el && nav) {
            const elRect = el.getBoundingClientRect();
            const navRect = nav.getBoundingClientRect();
            setIndicator({ left: elRect.left - navRect.left, scale: navRect.width ? elRect.width / navRect.width : 0 });
        }
    }, [tab]);

    useEffect(() => {
        getYoutubeStatus().then((s) => { setConfigured(s.configured); setQuota(s.quota); }).catch(() => setConfigured(false));

        const params = new URLSearchParams(window.location.search);
        const oauth = params.get("oauth");
        if (oauth === "success") {
            setOauthNotice({ type: "success", text: "YouTube account connected." });
            setTab("tracking");
        } else if (oauth === "error") {
            setOauthNotice({ type: "error", text: `OAuth connection failed (${params.get("reason") || "unknown reason"}).` });
            setTab("tracking");
        }
        if (oauth) {
            const url = new URL(window.location.href);
            url.searchParams.delete("oauth");
            url.searchParams.delete("reason");
            window.history.replaceState({}, "", url.toString());
        }
    }, []);

    return <section className="yt-page">
        <header className="yt-hero">
            <div className="yt-hero-mast">
                <h1 className="yt-hero-title">
                    {onNavigate
                        ? <a href="/" className="yt-hero-title-link" onClick={(e) => { e.preventDefault(); onNavigate("/"); }}>Reel Oracle</a>
                        : "Reel Oracle"}
                </h1>
                <p className="yt-hero-sub">Discover, analyse, predict, create, monitor and recommend — assembled as case files, powered by the YouTube Data API and heuristic scoring models.</p>
                <div className="yt-hero-top">
                    <span className="yt-hero-case">RO-INTEL-07 · OPEN CASE</span>
                    <span className="yt-stamp">Confidential Briefing</span>
                </div>
            </div>
            <div className="yt-hero-right">
                {quota && <div className="yt-quota">
                    <div className="yt-quota-label"><span>API quota today</span><strong>{quota.estimated_units_used_today.toLocaleString()} / {quota.daily_budget.toLocaleString()}</strong></div>
                    <div className="yt-quota-track"><div className="yt-quota-fill" style={{ transform: `scaleX(${Math.min(1, quota.estimated_units_used_today / quota.daily_budget)})` }} /></div>
                </div>}
                <button className="yt-theme-toggle" onClick={onToggleTheme} aria-label="Toggle theme">
                    <svg className="yt-theme-toggle-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                        {theme === "dark"
                            ? <circle cx="12" cy="12" r="4.5" />
                            : <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5Z" />}
                    </svg>
                    {theme === "dark" ? "Daylight" : "Night ops"}
                </button>
            </div>
        </header>

        {!configured && <div className="yt-empty"><p>YOUTUBE_API_KEY is not configured on the backend. Add it to <code>backend/.env</code>.</p></div>}
        {oauthNotice && <div className={oauthNotice.type === "success" ? "yt-empty yt-empty-success" : "yt-empty"}><p>{oauthNotice.text}</p></div>}

        <nav className="yt-tabs" ref={tabsNavRef}>
            <div className="yt-tabs-indicator" style={{ transform: `translateX(${indicator.left}px) scaleX(${indicator.scale})` }} />
            {TABS.map((t) => <button key={t.id} ref={(el) => { tabRefs.current[t.id] = el; }} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>{t.label}</button>)}
        </nav>

        <div className="yt-panel">
            {tab === "overview" && <OverviewTab onSelectTab={setTab} />}
            {tab === "discover" && <DiscoverTab initial={landingIntent?.tab === "discover" ? landingIntent : null} />}
            {tab === "analyse" && <AnalyseTab initial={landingIntent?.tab === "analyse" ? landingIntent : null} />}
            {tab === "predict" && <PredictTab />}
            {tab === "create" && <CreateTab />}
            {tab === "monitor" && <MonitorTab />}
            {tab === "recommend" && <RecommendTab />}
            {tab === "tracking" && <TrackingTab />}
        </div>
    </section>;
}

export default YoutubeIntel;
