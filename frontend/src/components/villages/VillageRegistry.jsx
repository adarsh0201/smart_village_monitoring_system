import React, { useState, useMemo } from 'react';
import { Search, Filter } from 'lucide-react';
import VillageTable from './VillageTable';

function VillageRegistry({
  villages = [],
  scenes = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  onNavigate = () => {},
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [districtFilter, setDistrictFilter] = useState('ALL');

  // Compute scene count per village
  const sceneCountsByVillage = useMemo(() => {
    const counts = {};
    scenes.forEach((s) => {
      counts[s.village] = (counts[s.village] || 0) + 1;
    });
    return counts;
  }, [scenes]);

  // Extract unique districts
  const districts = useMemo(() => {
    const set = new Set(villages.map((v) => v.district).filter(Boolean));
    return ['ALL', ...Array.from(set).sort()];
  }, [villages]);

  // Filter villages by query and district
  const filteredVillages = useMemo(() => {
    return villages.filter((v) => {
      const matchesSearch =
        v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        v.district.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesDistrict = districtFilter === 'ALL' || v.district === districtFilter;
      return matchesSearch && matchesDistrict;
    });
  }, [villages, searchQuery, districtFilter]);

  return (
    <div className="village-registry-page">
      <div className="page-header">
        <div className="page-header-title-block">
          <h1 className="page-title">Village Administrative Registry</h1>
          <p className="page-subtitle">
            Ground observation units mapped in PostGIS database &bull; Search, filter, and inspect pilot units
          </p>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search villages by name or district..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Filter size={15} style={{ color: 'var(--color-text-secondary)' }} />
          <select
            value={districtFilter}
            onChange={(e) => setDistrictFilter(e.target.value)}
            className="select-filter"
            aria-label="Filter by district"
          >
            {districts.map((d) => (
              <option key={d} value={d}>
                {d === 'ALL' ? 'All Rajasthan Districts' : `District: ${d}`}
              </option>
            ))}
          </select>
        </div>

        <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginLeft: 'auto' }}>
          Showing <strong>{filteredVillages.length}</strong> of {villages.length} registered units
        </span>
      </div>

      {/* Main Village Records Table */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <VillageTable
          villages={filteredVillages}
          selectedVillage={selectedVillage}
          onSelectVillage={onSelectVillage}
          onNavigateToGis={() => onNavigate('gis')}
          onNavigateToSatellite={() => onNavigate('satellite')}
          sceneCountsByVillage={sceneCountsByVillage}
        />
      </div>
    </div>
  );
}

export default VillageRegistry;
