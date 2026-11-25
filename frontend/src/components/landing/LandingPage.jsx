import React from 'react';
import {
  Landmark,
  LayoutDashboard,
  Layers,
  Map,
  GitCompare,
  ArrowRight,
  BookOpen,
  Compass,
  Satellite,
  ShieldCheck,
  Database,
  CheckCircle2,
} from 'lucide-react';

/**
 * Gram Darpan — Official Spatial Intelligence Portal Landing Page
 * Visual Theme: Earth & Agriculture Editorial (Strictly Light Mode)
 */
export function LandingPage({
  onOpenDashboard = () => {},
  onNavigateModule = () => {},
  villageCount = 0,
  sceneCount = 0,
  isConnected = true,
}) {
  const modules = [
    {
      id: 'analytics',
      options: { initialTab: 'lulc' },
      code: 'Module 01',
      title: 'AI Land Cover (LULC)',
      description:
        'Hectare analytics and terrain breakdowns across cropland, tree canopy, settlements, and surface water bodies.',
      detail: '6-Feature Random Forest Classification · 10m Grid',
      actionLabel: 'Open Land Cover Analytics',
      icon: Layers,
    },
    {
      id: 'gis',
      options: {},
      code: 'Module 02',
      title: 'GIS Spatial Explorer',
      description:
        'Interactive map viewer and index overlays combining administrative village boundaries with satellite telemetry.',
      detail: 'EPSG:4326 PostGIS Vector & Raster Layers',
      actionLabel: 'Open GIS Map Explorer',
      icon: Map,
    },
    {
      id: 'change',
      options: {},
      code: 'Module 03',
      title: 'Temporal Change',
      description:
        'Date-to-date urban and environmental change detection across seasonal crop cycles and surface water bodies.',
      detail: 'Bi-Temporal Spectral Differencing (T₂ − T₁)',
      actionLabel: 'Open Change Detection',
      icon: GitCompare,
    },
  ];

  const methodologyStages = [
    {
      step: 'Stage 01',
      title: 'Multi-Sensor Earth Observation',
      body: 'Automated acquisition of Sentinel-1 C-band Dual-Pol SAR radar, Sentinel-2 Level-2A optical reflectance, and Copernicus DEM elevation rasters clipped strictly to official village AOIs.',
      icon: Satellite,
    },
    {
      step: 'Stage 02',
      title: 'Cloud-Masked Bio-Physical Fusion',
      body: 'Scene Classification Layer (SCL) cloud masking paired with NDVI and NDWI spectral computation enables reliable land-surface observation even under partial seasonal cloud cover.',
      icon: Database,
    },
    {
      step: 'Stage 03',
      title: 'Verified Administrative Decision Metrics',
      body: 'Deterministic 10m × 10m pixel accounting converts classified land parcels directly into auditable hectare summaries ready for block and district review.',
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="min-h-screen bg-[#F7F5F0] text-[#2C2A29] font-sans antialiased flex flex-col">
      {/* ── Top Navigation Header ── */}
      <header className="sticky top-0 z-40 bg-white border-b border-[#E2DAC6] shadow-[0_1px_2px_rgba(44,42,41,0.05)]">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-4 flex flex-wrap items-center justify-between gap-4">
          {/* Official Brand Logo & Title */}
          <a
            href="#overview"
            className="flex items-center gap-3.5 text-[#2C2A29] no-underline focus:outline-none focus:ring-2 focus:ring-emerald-700 rounded-md"
          >
            <div className="w-11 h-11 rounded-md bg-emerald-700 border border-emerald-800 text-white flex items-center justify-center shrink-0">
              <Landmark className="w-5 h-5" aria-hidden="true" />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-bold tracking-tight text-[#2C2A29] leading-tight">
                Gram Darpan
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-stone-600">
                Rural Spatial Intelligence Portal
              </span>
            </div>
          </a>

          {/* Navigation Anchors + Primary Dashboard Action */}
          <nav
            aria-label="Primary Landing Navigation"
            className="flex flex-wrap items-center gap-3 sm:gap-6"
          >
            <a
              href="#overview"
              className="inline-flex items-center gap-2 px-3 py-2 text-base font-semibold text-[#2C2A29] hover:text-emerald-700 rounded-md transition-colors"
            >
              <Compass className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Overview</span>
            </a>

            <a
              href="#methodology"
              className="inline-flex items-center gap-2 px-3 py-2 text-base font-semibold text-[#2C2A29] hover:text-emerald-700 rounded-md transition-colors"
            >
              <BookOpen className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Methodology</span>
            </a>

            <button
              type="button"
              onClick={onOpenDashboard}
              className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-md bg-emerald-700 hover:bg-emerald-800 text-white text-base font-semibold border border-emerald-800 shadow-[0_1px_2px_rgba(44,42,41,0.12)] transition-colors cursor-pointer"
            >
              <LayoutDashboard className="w-4 h-4" aria-hidden="true" />
              <span>Open Dashboard</span>
            </button>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* ── Hero Section ── */}
        <section
          id="overview"
          className="border-b border-[#E2DAC6] bg-[#F7F5F0] py-16 lg:py-22"
        >
          <div className="max-w-7xl mx-auto px-6 lg:px-10">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-start">
              {/* Editorial Headline & Primary CTA */}
              <div className="lg:col-span-7 space-y-6">
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-white border border-[#E2DAC6] rounded-md text-sm font-semibold text-emerald-800 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                  <span>Official WebGIS Decision Support Platform</span>
                </div>

                <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-[#2C2A29] leading-[1.15]">
                  Precision monitoring for sustainable rural governance
                </h1>

                <p className="text-lg text-stone-700 leading-relaxed max-w-2xl">
                  Gram Darpan equips district magistrates, panchayat officers, and agricultural planners with audited multi-modal satellite intelligence. By fusing Sentinel-1 radar, Sentinel-2 optical imagery, and Copernicus digital elevation models, every monitored village receives verified 10-meter land-cover accounting and spatial change diagnostics.
                </p>

                <div className="flex flex-wrap items-center gap-4 pt-2">
                  <button
                    type="button"
                    onClick={onOpenDashboard}
                    className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-md bg-emerald-700 hover:bg-emerald-800 text-white text-base font-semibold border border-emerald-800 shadow-[0_2px_4px_rgba(44,42,41,0.12)] transition-colors cursor-pointer"
                  >
                    <LayoutDashboard className="w-5 h-5" aria-hidden="true" />
                    <span>Enter Operational Dashboard</span>
                    <ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </button>

                  <a
                    href="#methodology"
                    className="inline-flex items-center gap-2 px-6 py-3.5 rounded-md bg-white hover:bg-stone-100 text-[#2C2A29] text-base font-semibold border border-[#E2DAC6] shadow-[0_1px_2px_rgba(44,42,41,0.05)] transition-colors"
                  >
                    <BookOpen className="w-5 h-5 text-emerald-700" aria-hidden="true" />
                    <span>Read Technical Methodology</span>
                  </a>
                </div>
              </div>

              {/* Authoritative Ledger Card (Report-Style Institutional Summary) */}
              <div className="lg:col-span-5">
                <div className="bg-white border border-[#E2DAC6] rounded-lg p-7 shadow-[0_2px_6px_rgba(44,42,41,0.06)]">
                  <div className="flex items-center justify-between pb-4 mb-5 border-b border-[#E2DAC6]">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 block">
                        System Registry Briefing
                      </span>
                      <h2 className="text-lg font-bold text-[#2C2A29] mt-0.5">
                        Operational Telemetry Specifications
                      </h2>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" aria-hidden="true" />
                      <span>{isConnected ? 'System Active' : 'Standby'}</span>
                    </span>
                  </div>

                  <dl className="divide-y divide-[#EDE7D9] text-base">
                    <div className="py-3.5 flex items-center justify-between gap-4">
                      <dt className="font-medium text-stone-600">Registered Administrative Units</dt>
                      <dd className="font-bold text-[#2C2A29] font-mono">
                        {villageCount > 0 ? `${villageCount} Villages` : 'PostGIS Spatial Registry'}
                      </dd>
                    </div>
                    <div className="py-3.5 flex items-center justify-between gap-4">
                      <dt className="font-medium text-stone-600">Satellite Acquisitions Indexed</dt>
                      <dd className="font-bold text-[#2C2A29] font-mono">
                        {sceneCount > 0 ? `${sceneCount} Scenes` : 'Sentinel-1 & Sentinel-2'}
                      </dd>
                    </div>
                    <div className="py-3.5 flex items-center justify-between gap-4">
                      <dt className="font-medium text-stone-600">Ground Sampling Distance</dt>
                      <dd className="font-bold text-[#2C2A29] font-mono">10m &times; 10m (100 m&sup2;)</dd>
                    </div>
                    <div className="py-3.5 flex items-center justify-between gap-4">
                      <dt className="font-medium text-stone-600">Coordinate Reference Standard</dt>
                      <dd className="font-bold text-[#2C2A29] font-mono">EPSG:4326 (WGS 84)</dd>
                    </div>
                    <div className="pt-3.5 flex items-center justify-between gap-4">
                      <dt className="font-medium text-stone-600">Feature Fusion Architecture</dt>
                      <dd className="font-semibold text-emerald-800">SAR + Optical + DEM</dd>
                    </div>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Explore Modules (Core 3-Column Interactive Routing Grid) ── */}
        <section
          aria-labelledby="explore-modules-heading"
          className="py-16 lg:py-20 bg-[#F7F5F0]"
        >
          <div className="max-w-7xl mx-auto px-6 lg:px-10">
            <div className="pb-5 mb-10 border-b-2 border-[#E2DAC6] flex flex-wrap items-end justify-between gap-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 block mb-1">
                  Core Portal Workspaces
                </span>
                <h2
                  id="explore-modules-heading"
                  className="text-2xl sm:text-3xl font-bold text-[#2C2A29]"
                >
                  Explore Operational Modules
                </h2>
              </div>
              <p className="text-base text-stone-600 max-w-xl">
                Select a specialized geospatial workspace below to inspect village land classification, interactive GIS layers, or temporal environmental trends.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-7">
              {modules.map((mod) => {
                const Icon = mod.icon;
                return (
                  <button
                    key={mod.id}
                    type="button"
                    onClick={() => onNavigateModule(mod.id, mod.options)}
                    className="group text-left bg-white border border-[#E2DAC6] hover:border-emerald-700 rounded-lg p-7 shadow-[0_1px_3px_rgba(44,42,41,0.06)] hover:shadow-[0_4px_10px_rgba(44,42,41,0.08)] transition-all flex flex-col justify-between gap-6 cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-700"
                  >
                    <div className="space-y-4">
                      <div className="flex items-center justify-between gap-3 pb-3 border-b border-[#EDE7D9]">
                        <div className="inline-flex items-center gap-2.5 text-emerald-800 font-semibold text-sm">
                          <span className="w-9 h-9 rounded-md bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
                            <Icon className="w-5 h-5" aria-hidden="true" />
                          </span>
                          <span>{mod.code}</span>
                        </div>
                        <span className="text-xs font-semibold uppercase tracking-wide text-stone-600">
                          Active Module
                        </span>
                      </div>

                      <div>
                        <h3 className="text-xl font-bold text-[#2C2A29] group-hover:text-emerald-800 transition-colors">
                          {mod.title}
                        </h3>
                        <p className="mt-2.5 text-base text-stone-700 leading-relaxed">
                          {mod.description}
                        </p>
                      </div>
                    </div>

                    <div className="pt-4 border-t border-[#EDE7D9] space-y-3 w-full">
                      <div className="text-xs font-mono font-semibold text-stone-600">
                        {mod.detail}
                      </div>
                      <div className="inline-flex items-center gap-2 text-base font-bold text-emerald-700 group-hover:text-emerald-800">
                        <span>{mod.actionLabel}</span>
                        <ArrowRight
                          className="w-4 h-4 transition-transform group-hover:translate-x-1"
                          aria-hidden="true"
                        />
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── Methodology Section (Target for Header Anchor Link) ── */}
        <section
          id="methodology"
          aria-labelledby="methodology-heading"
          className="py-16 lg:py-20 bg-white border-t border-[#E2DAC6]"
        >
          <div className="max-w-7xl mx-auto px-6 lg:px-10">
            <div className="pb-5 mb-10 border-b-2 border-[#E2DAC6] flex flex-wrap items-end justify-between gap-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 block mb-1">
                  Scientific Protocol &amp; Verification
                </span>
                <h2
                  id="methodology-heading"
                  className="text-2xl sm:text-3xl font-bold text-[#2C2A29]"
                >
                  Data &amp; Classification Methodology
                </h2>
              </div>
              <p className="text-base text-stone-600 max-w-xl">
                Transparent, reproducible geospatial processing calibrated for Indian agro-climatic landscapes and official district audits.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-7">
              {methodologyStages.map((stage) => {
                const StageIcon = stage.icon;
                return (
                  <article
                    key={stage.step}
                    className="bg-[#F7F5F0] border border-[#E2DAC6] rounded-lg p-7 flex flex-col gap-4"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-10 h-10 rounded-md bg-white border border-[#E2DAC6] flex items-center justify-center text-emerald-700 shrink-0">
                        <StageIcon className="w-5 h-5" aria-hidden="true" />
                      </span>
                      <span className="text-sm font-bold uppercase tracking-wider text-emerald-800">
                        {stage.step}
                      </span>
                    </div>

                    <h3 className="text-lg font-bold text-[#2C2A29]">{stage.title}</h3>
                    <p className="text-base text-stone-700 leading-relaxed">{stage.body}</p>
                  </article>
                );
              })}
            </div>

            {/* Bottom Callout Strip */}
            <div className="mt-12 bg-[#F7F5F0] border border-[#E2DAC6] rounded-lg p-7 flex flex-wrap items-center justify-between gap-6">
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-[#2C2A29]">
                  Ready to review village-level spatial reports?
                </h3>
                <p className="text-base text-stone-700">
                  Access live PostGIS village boundaries, spectral indices, and LULC hectare tables inside the control portal.
                </p>
              </div>
              <button
                type="button"
                onClick={onOpenDashboard}
                className="inline-flex items-center gap-2.5 px-6 py-3 rounded-md bg-emerald-700 hover:bg-emerald-800 text-white text-base font-semibold border border-emerald-800 shadow-[0_1px_2px_rgba(44,42,41,0.1)] transition-colors cursor-pointer"
              >
                <LayoutDashboard className="w-5 h-5" aria-hidden="true" />
                <span>Open Dashboard</span>
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* ── Institutional Portal Footer ── */}
      <footer className="bg-white border-t border-[#E2DAC6] py-8">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 flex flex-wrap items-center justify-between gap-4 text-sm text-stone-600">
          <div className="flex items-center gap-2.5 font-semibold text-[#2C2A29]">
            <Landmark className="w-4 h-4 text-emerald-700" aria-hidden="true" />
            <span>Gram Darpan &mdash; Smart Village Monitoring WebGIS System</span>
          </div>
          <div className="flex flex-wrap items-center gap-6">
            <a href="#overview" className="hover:text-emerald-700 font-medium">
              Overview
            </a>
            <a href="#methodology" className="hover:text-emerald-700 font-medium">
              Methodology
            </a>
            <button
              type="button"
              onClick={onOpenDashboard}
              className="inline-flex items-center gap-1.5 font-semibold text-emerald-700 hover:text-emerald-800 cursor-pointer"
            >
              <LayoutDashboard className="w-4 h-4" aria-hidden="true" />
              <span>Open Dashboard</span>
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
