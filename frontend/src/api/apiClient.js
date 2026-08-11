import axios from "axios";

export const API_BASE_URL = (
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8010"
).replace(/\/$/, "");

export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

export default apiClient;
