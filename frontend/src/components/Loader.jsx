import "./Loader.css";

function Loader({ label = "Loading" }) {
    return <div className="yt-loader" role="status" aria-live="polite">
        <div className="yt-loader-bars" aria-hidden="true">
            <span className="yt-skeleton" />
            <span className="yt-skeleton" />
            <span className="yt-skeleton" />
        </div>
        <span>{label}</span>
    </div>;
}

export default Loader;
