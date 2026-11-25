import React, { useState } from 'react';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

function AppLayout({
  activePage,
  onNavigate,
  isConnected,
  isLoading,
  onRefresh,
  villages = [],
  scenes = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  children,
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      <a href="#main-workspace" className="skip-link">
        Skip to main dashboard content
      </a>

      {/* Mobile Drawer Backdrop (Solid warm scrim, no glassmorphism) */}
      <div
        className={`sidebar-overlay ${isMobileOpen ? 'active' : ''}`}
        onClick={() => setIsMobileOpen(false)}
        aria-hidden="true"
      />

      {/* Institutional Navigation Sidebar */}
      <Sidebar
        activePage={activePage}
        onNavigate={onNavigate}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
        isConnected={isConnected}
        villageCount={villages.length}
        sceneCount={scenes.length}
      />

      {/* Main Content Area */}
      <div className={`main-wrapper ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Topbar
          activePage={activePage}
          onOpenMobile={() => setIsMobileOpen(true)}
          isConnected={isConnected}
          isLoading={isLoading}
          onRefresh={onRefresh}
          villages={villages}
          selectedVillage={selectedVillage}
          onSelectVillage={onSelectVillage}
        />

        <main id="main-workspace" className="page-workspace" tabIndex={-1}>
          {children}
        </main>

        <footer className="institutional-footer" aria-label="System Governance Footer">
          <div>
            <strong>Smart Village Monitoring System</strong> &bull; WebGIS Decision Support Portal
          </div>
          <div>
            Spatial Reference: <code className="cell-code">EPSG:4326 (WGS 84)</code> &bull;{' '}
            {villages.length} Registered Administrative Units
          </div>
        </footer>
      </div>
    </div>
  );
}

export default AppLayout;
