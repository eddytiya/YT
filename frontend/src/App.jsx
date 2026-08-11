import { Suspense, lazy, useEffect, useState } from "react";

import Landing from "./pages/Landing";
import Loader from "./components/Loader";

const YoutubeIntel = lazy(() => import("./pages/YoutubeIntel"));

function getInitialTheme() {
    const stored = localStorage.getItem("yt-theme");
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function normalizePath(pathname) {
    return pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
}

function useRoute() {
    const [path, setPath] = useState(normalizePath(window.location.pathname));

    useEffect(() => {
        const onPop = () => setPath(normalizePath(window.location.pathname));
        window.addEventListener("popstate", onPop);
        return () => window.removeEventListener("popstate", onPop);
    }, []);

    const navigate = (to) => {
        if (to !== window.location.pathname) window.history.pushState({}, "", to);
        setPath(to);
        window.scrollTo(0, 0);
    };

    return [path, navigate];
}

function App() {
    const [theme, setTheme] = useState(getInitialTheme);
    const [path, navigate] = useRoute();

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("yt-theme", theme);
    }, [theme]);

    const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

    if (path === "/app") {
        return <Suspense fallback={<div className="yt-route-fallback"><Loader label="Loading the briefing" /></div>}>
            <YoutubeIntel theme={theme} onToggleTheme={toggleTheme} onNavigate={navigate} />
        </Suspense>;
    }
    return <Landing theme={theme} onToggleTheme={toggleTheme} onNavigate={navigate} />;
}

export default App;
