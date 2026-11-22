import React from 'react';

function StatCard({ label, value, subtext, icon: Icon, colorClass = "green" }) {
  return (
    <div className="kpi-card">
      <div className={`kpi-icon-box ${colorClass}`}>
        <Icon size={22} />
      </div>
      <div className="kpi-content">
        <span className="kpi-label">{label}</span>
        <h3 className="kpi-value">{value}</h3>
        {subtext && <span className="kpi-subtext">{subtext}</span>}
      </div>
    </div>
  );
}

export default StatCard;

