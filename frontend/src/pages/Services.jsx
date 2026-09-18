import { useState } from "react";
import ConnectionsTab from "./ConnectionsTab.jsx";
import RecentRunsTab from "./RecentRunsTab.jsx";
import HistoryTab from "./HistoryTab.jsx";

export default function Services() {
  const [activeTab, setActiveTab] = useState("connections");
  const [historyFilter, setHistoryFilter] = useState(null);

  const goToHistory = (connectionId) => {
    setHistoryFilter(connectionId);
    setActiveTab("history");
  };

  return (
    <div>
      <h1>Services</h1>

      <div className="tabs page-tabs">
        <button
          className={activeTab === "connections" ? "tab active" : "tab"}
          onClick={() => setActiveTab("connections")}
        >
          Connections
        </button>
        <button
          className={activeTab === "recent" ? "tab active" : "tab"}
          onClick={() => setActiveTab("recent")}
        >
          Recent Runs
        </button>
        <button
          className={activeTab === "history" ? "tab active" : "tab"}
          onClick={() => setActiveTab("history")}
        >
          History
        </button>
      </div>

      <div className="tab-content">
        {activeTab === "connections" && (
          <ConnectionsTab onViewHistory={goToHistory} />
        )}
        {activeTab === "recent" && <RecentRunsTab />}
        {activeTab === "history" && (
          <HistoryTab
            connectionFilter={historyFilter}
            onClearFilter={() => setHistoryFilter(null)}
          />
        )}
      </div>
    </div>
  );
}
