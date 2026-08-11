"""
Creator-network analysis over a collected set of search results for a topic.

This models relationships observable in your own fetched dataset (which
channels keep appearing together for a topic, who's most central) - it is
not a reconstruction of YouTube's private recommendation graph.
"""

import networkx as nx


def build_creator_network(search_items: list[dict]) -> dict:
    """Nodes = channels that appeared in the search results. Edges connect
    channels whose videos share title keywords (same conversation)."""

    from app.services.youtube.analytics import _extract_keywords

    channel_titles: dict[str, str] = {}
    channel_keywords: dict[str, set] = {}

    for item in search_items:
        snippet = item.get("snippet", {})
        channel_id = snippet.get("channelId")
        if not channel_id:
            continue
        channel_titles[channel_id] = snippet.get("channelTitle", channel_id)
        keywords = set(_extract_keywords(snippet.get("title", "")).keys())
        channel_keywords.setdefault(channel_id, set()).update(keywords)

    graph = nx.Graph()
    for channel_id, title in channel_titles.items():
        graph.add_node(channel_id, title=title)

    channel_ids = list(channel_keywords.keys())
    for i in range(len(channel_ids)):
        for j in range(i + 1, len(channel_ids)):
            a, b = channel_ids[i], channel_ids[j]
            shared = channel_keywords[a] & channel_keywords[b]
            if len(shared) >= 2:
                graph.add_edge(a, b, weight=len(shared), shared_keywords=list(shared)[:5])

    if graph.number_of_nodes() == 0:
        return {"nodes": [], "edges": [], "communities": [], "most_central": []}

    pagerank = nx.pagerank(graph) if graph.number_of_edges() > 0 else {n: 0 for n in graph.nodes}

    communities = []
    if graph.number_of_edges() > 0:
        for community in nx.algorithms.community.greedy_modularity_communities(graph):
            if len(community) >= 2:
                communities.append([
                    {"channel_id": cid, "title": channel_titles.get(cid, cid)}
                    for cid in community
                ])

    most_central = sorted(pagerank.items(), key=lambda kv: kv[1], reverse=True)[:5]

    return {
        "nodes": [{"channel_id": cid, "title": title} for cid, title in channel_titles.items()],
        "edges": [
            {"source": u, "target": v, "shared_keywords": data.get("shared_keywords", [])}
            for u, v, data in graph.edges(data=True)
        ],
        "communities": communities,
        "most_central": [
            {"channel_id": cid, "title": channel_titles.get(cid, cid), "centrality": round(score, 4)}
            for cid, score in most_central if score > 0
        ],
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
    }
