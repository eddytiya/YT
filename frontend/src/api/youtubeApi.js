import apiClient, { API_BASE_URL } from "./apiClient";

export const getYoutubeStatus = async () => (await apiClient.get("/status")).data;

export const getVideoCategories = async (regionCode = "US") =>
    (await apiClient.get("/video-categories", { params: { region_code: regionCode } })).data;

export const getI18nRegions = async () => (await apiClient.get("/i18n/regions")).data;
export const getI18nLanguages = async () => (await apiClient.get("/i18n/languages")).data;
export const getChannelSections = async (channelId) => (await apiClient.get(`/channel-sections/${channelId}`)).data;

export const getLiveNow = async (topic, maxResults = 15) =>
    (await apiClient.get("/discover/live-now", { params: { topic, max_results: maxResults } })).data;

export const getUpcoming = async (topic, maxResults = 15) =>
    (await apiClient.get("/discover/upcoming", { params: { topic, max_results: maxResults } })).data;

export const searchYoutube = async ({ q, maxResults = 10, order = "relevance" }) =>
    (await apiClient.get("/search", { params: { q, max_results: maxResults, order } })).data;

export const getYoutubeTrending = async ({ regionCode = "IN", categoryId = "", maxResults = 20 } = {}) =>
    (await apiClient.get("/trending", { params: { region_code: regionCode, ...(categoryId && { category_id: categoryId }), max_results: maxResults } })).data;

export const getChannelRecentVideos = async (channelId, maxResults = 20) =>
    (await apiClient.get(`/channels/${channelId}/recent-videos`, { params: { max_results: maxResults } })).data;

// Discover
export const getTrendRadar = async (topics, maxResults = 15, regionCode = "", categoryId = "", videoDuration = "") =>
    (await apiClient.get("/discover/trend-radar", { params: { topics, max_results: maxResults, ...(regionCode && { region_code: regionCode }), ...(categoryId && { category_id: categoryId }), ...(videoDuration && { video_duration: videoDuration }) } })).data;

export const getOpportunities = async (ownChannelId, competitorChannelIds, maxResults = 20) =>
    (await apiClient.get("/discover/opportunities", { params: { own_channel_id: ownChannelId, competitor_channel_ids: competitorChannelIds, max_results: maxResults } })).data;

export const getCompetitors = async (channelIds) =>
    (await apiClient.get("/discover/competitors", { params: { channel_ids: channelIds } })).data;

export const getCreatorNetwork = async (topic, maxResults = 30) =>
    (await apiClient.get("/discover/creator-network", { params: { topic, max_results: maxResults } })).data;

export const getTopicIntelligence = async (query, competitors = "", maxResults = 8) =>
    (await apiClient.get("/discover/topic-intelligence", { params: { query, competitors, max_results: maxResults } })).data;

export const semanticSearch = async (q, maxResults = 15) =>
    (await apiClient.get("/discover/semantic-search", { params: { q, max_results: maxResults } })).data;

// Analyse
export const analyzeVideo = async (videoId) =>
    (await apiClient.get(`/analyze/video/${videoId}`)).data;

export const analyzeComments = async (videoId, maxResults = 50, multilingual = false) =>
    (await apiClient.get(`/analyze/comments/${videoId}`, { params: { max_results: maxResults, multilingual } })).data;

export const analyzeThumbnail = async (videoId) =>
    (await apiClient.get("/analyze/thumbnail", { params: { video_id: videoId } })).data;

export const analyzeAspects = async (videoId, maxResults = 50) =>
    (await apiClient.get(`/analyze/aspects/${videoId}`, { params: { max_results: maxResults } })).data;

export const analyzeMisleading = async (videoId, maxResults = 50) =>
    (await apiClient.get(`/analyze/misleading/${videoId}`, { params: { max_results: maxResults } })).data;

export const analyzeBrandSafety = async (channelId, sampleSize = 5) =>
    (await apiClient.get(`/analyze/brand-safety/${channelId}`, { params: { sample_size: sampleSize } })).data;

export const analyzePlaylist = async (playlistId, maxResults = 50) =>
    (await apiClient.get(`/analyze/playlist/${playlistId}`, { params: { max_results: maxResults } })).data;

export const analyzeBotRisk = async (videoId, maxResults = 50) =>
    (await apiClient.get(`/analyze/bot-risk/${videoId}`, { params: { max_results: maxResults } })).data;

export const analyzeChannelAudit = async (channelId, sampleSize = 5) =>
    (await apiClient.get(`/analyze/channel-audit/${channelId}`, { params: { sample_size: sampleSize } })).data;

// Predict
export const predictVirality = async (videoId) =>
    (await apiClient.get(`/predict/virality/${videoId}`)).data;

export const predictChannelGrowth = async (channelId) =>
    (await apiClient.get(`/predict/channel-growth/${channelId}`)).data;

export const predictViralityMl = async (videoId) =>
    (await apiClient.get(`/predict/virality-ml/${videoId}`)).data;

export const predictChannelGrowthMl = async (channelId) =>
    (await apiClient.get(`/predict/channel-growth-ml/${channelId}`)).data;

// Create
export const createTitles = async (topic, style = "educational") =>
    (await apiClient.post("/create/titles", { topic, style })).data;

export const getUploadTiming = async (channelId, maxResults = 30) =>
    (await apiClient.get(`/create/upload-timing/${channelId}`, { params: { max_results: maxResults } })).data;

export const getPersonalizedInsights = async () =>
    (await apiClient.get("/create/personalized-insights")).data;

// Monitor
export const monitorSentiment = async (videoId, maxResults = 50, multilingual = false) =>
    (await apiClient.get(`/monitor/sentiment/${videoId}`, { params: { max_results: maxResults, multilingual } })).data;

export const monitorAnomalies = async (channelId, maxResults = 20) =>
    (await apiClient.get(`/monitor/anomalies/${channelId}`, { params: { max_results: maxResults } })).data;

export const monitorLiveChat = async (videoId, maxResults = 200) =>
    (await apiClient.get(`/monitor/live-chat/${videoId}`, { params: { max_results: maxResults } })).data;

// Recommend
export const recommendSimilar = async (videoId, maxResults = 10) =>
    (await apiClient.get(`/recommend/similar/${videoId}`, { params: { max_results: maxResults } })).data;

export const recommendNextVideoIdeas = async (ownChannelId, competitorChannelIds, maxResults = 20) =>
    (await apiClient.get("/recommend/next-video-ideas", { params: { own_channel_id: ownChannelId, competitor_channel_ids: competitorChannelIds, max_results: maxResults } })).data;

// Tracking + history
export const trackChannel = async (channelId, label) =>
    (await apiClient.post("/track/channels", { channel_id: channelId, label })).data;

export const listTrackedChannels = async () =>
    (await apiClient.get("/track/channels")).data;

export const untrackChannel = async (trackedId) =>
    (await apiClient.delete(`/track/channels/${trackedId}`)).data;

export const trackVideo = async (videoId, label) =>
    (await apiClient.post("/track/videos", { video_id: videoId, label })).data;

export const listTrackedVideos = async () =>
    (await apiClient.get("/track/videos")).data;

export const untrackVideo = async (trackedId) =>
    (await apiClient.delete(`/track/videos/${trackedId}`)).data;

export const getChannelHistory = async (channelId, limit = 90) =>
    (await apiClient.get(`/history/channel/${channelId}`, { params: { limit } })).data;

export const getVideoHistory = async (videoId, limit = 90) =>
    (await apiClient.get(`/history/video/${videoId}`, { params: { limit } })).data;

export const getTrackingDigest = async () =>
    (await apiClient.get("/track/digest")).data;

export const channelHistoryCsvUrl = (channelId) => `${API_BASE_URL}/history/channel/${channelId}/export.csv`;
export const videoHistoryCsvUrl = (videoId) => `${API_BASE_URL}/history/video/${videoId}/export.csv`;

// Derived-from-stored-history features - all zero additional YouTube quota,
// pure reads over snapshots the background poller already collected.
export const getChannelLeaderboard = async (metric, limit = 10) =>
    (await apiClient.get("/track/leaderboard/channels", { params: { metric, limit } })).data;

export const getVideoLeaderboard = async (metric, limit = 10) =>
    (await apiClient.get("/track/leaderboard/videos", { params: { metric, limit } })).data;

export const getTrackingMilestones = async (limit = 20) =>
    (await apiClient.get("/track/milestones", { params: { limit } })).data;

export const compareChannels = async (channelIds, limit = 90) =>
    (await apiClient.get("/track/compare-channels", { params: { channel_ids: channelIds, limit } })).data;

export const getContentCalendar = async (channelA, channelB, maxResults = 20) =>
    (await apiClient.get("/discover/content-calendar", { params: { channel_a: channelA, channel_b: channelB, max_results: maxResults } })).data;

// OAuth creator analytics
export const getOAuthStatus = async () =>
    (await apiClient.get("/oauth/status")).data;

export const getOAuthAuthorizeUrl = async () =>
    (await apiClient.get("/oauth/authorize")).data;

export const disconnectOAuth = async () =>
    (await apiClient.delete("/oauth/disconnect")).data;

export const getOAuthAnalytics = async (days = 28) =>
    (await apiClient.get("/oauth/analytics", { params: { days } })).data;
