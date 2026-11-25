import React from 'react';
import {
  Home,
  LayoutDashboard,
  Map,
  Building2,
  Satellite,
  Activity,
  GitCompare,
  FileText,
  ChevronLeft,
  ChevronRight,
  Layers,
} from 'lucide-react';

function Sidebar({
  activePage,
  onNavigate,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
  isConnected,
  villageCount = 0,
  sceneCount = 0,
}) {
  const navSections = [
    {
      title: 'Geospatial Workspaces',
      items: [
        { id: 'landing', label: 'Gram Darpan Home', icon: Home },
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'gis', label: 'GIS Explorer', icon: Map, badge: villageCount > 0 ? villageCount : null },
        { id: 'villages', label: 'Village Registry', icon: Building2 },
        { id: 'satellite', label: 'Satellite Imagery', icon: Satellite, badge: sceneCount > 0 ? sceneCount : null },
      ],
    },
    {
      title: 'Remote Sensing Analytics',
      items: [
        { id: 'analytics', label: 'Environmental Analytics', icon: Activity },
        { id: 'change', label: 'Change Detection', icon: GitCompare },
        { id: 'reports', label: 'Reports', icon: FileText },
      ],
    },
  ];

  return (
    <aside
      className={`app-sidebar ${isCollapsed ? 'collapsed' : ''} ${
        isMobileOpen ? 'mobile-open' : ''
      }`}
      aria-label="Primary Sidebar Navigation"
    >
      {/* Sidebar Header & Brand */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="brand-logo-icon" aria-hidden="true">
            <Layers size={20} />
          </div>
          {!isCollapsed && (
            <div className="brand-text-block">
              <span className="brand-title">Gram Darpan</span>
              <span className="brand-subtitle">Smart Village WebGIS</span>
            </div>
          )}
        </div>

        <button
          type="button"
          className="btn-sidebar-toggle"
          onClick={onToggleCollapse}
          aria-label={isCollapsed ? 'Expand sidebar navigation' : 'Collapse sidebar navigation'}
        >
          {isCollapsed ? (
            <>
              <ChevronRight size={15} />
              <span>Expand</span>
            </>
          ) : (
            <>
              <ChevronLeft size={15} />
              <span>Hide</span>
            </>
          )}
        </button>
      </div>

      {/* Nav Items — All icons always carry text labels */}
      <nav className="sidebar-nav-container" aria-label="Workspace Sections">
        {navSections.map((section) => (
          <div key={section.title} className="nav-section-group">
            {!isCollapsed && <span className="nav-section-title">{section.title}</span>}
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`nav-item-btn ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    onNavigate(item.id);
                    onCloseMobile();
                  }}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <span className="nav-item-icon" aria-hidden="true">
                    <Icon size={18} />
                  </span>
                  <span className="nav-item-label">{item.label}</span>
                  {!isCollapsed && item.badge && (
                    <span className="nav-item-badge">{item.badge}</span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Sidebar Footer: System Status */}
      <div className="sidebar-footer">
        <div className="system-status-pill">
          <span className={`status-dot ${isConnected ? 'online' : 'offline'}`} aria-hidden="true"></span>
          <span>
            {isCollapsed
              ? isConnected
                ? 'Online'
                : 'Offline'
              : isConnected
                ? 'PostGIS Server Online'
                : 'Server Disconnected'}
          </span>
        </div>
        {!isCollapsed && (
          <div className="system-meta-text">
            <span>Django 5.2 REST &bull; PostGIS 3.6</span>
            <br />
            <span>Sentinel-2 L2A &bull; GDAL 3.9.2</span>
          </div>
        )}
      </div>
    </aside>
  );
}

export default Sidebar;
