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
      {/* Mobile Drawer Backdrop */}
      <div
        className={`sidebar-overlay ${isMobileOpen ? 'active' : ''}`}
        onClick={() => setIsMobileOpen(false)}
      />

      {/* Sidebar Navigation */}
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

      {/* Main Workspace Area */}
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

        <main className="page-workspace">{children}</main>
      </div>
    </div>
  );
}

export default AppLayout;

