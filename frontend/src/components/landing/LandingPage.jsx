import React from 'react';
import {
  Landmark,
  LayoutDashboard,
  Layers,
  Map,
  GitCompare,
  ArrowRight,
  Compass,
  Satellite,
  Cpu,
  ClipboardCheck,
  Leaf,
  CloudRain,
  Grid,
  Trees,
  Waves,
  Home,
  Wheat,
  CheckCircle2,
  MapPin,
  Workflow,
  Calendar,
} from 'lucide-react';

/**
 * Gram Darpan — Official Spatial Intelligence Portal for Rural Governance
 * Aesthetic: Printed Atlas meets Interactive GIS Tool (Strictly Light Mode)
 */
export function LandingPage({
  onOpenDashboard = () => {},
  onNavigateModule = () => {},
  villageCount = 0,
  sceneCount = 0,
  isConnected = true,
}) {
  const processSteps = [
    {
      stepNumber: 'Step 01',
      title: 'Select & Acquire',
      description:
        'Choose a village jurisdiction. The system automatically fetches 10m-resolution Sentinel-1 (Radar) and Sentinel-2 (Optical) data.',
      badgeText: '10m Multi-Sensor Sync',
      highlights: ['Sentinel-1 SAR', 'Sentinel-2 L2A', 'Copernicus DEM'],
      icon: Satellite,
    },
    {
      stepNumber: 'Step 02',
      title: 'AI Processing',
      description:
        'Navigate to the Analytics Engine where our Random Forest model classifies pixels into Cropland, Trees, Water, and Settlements.',
      badgeText: '6-Feature Fusion',
      highlights: ['SCL Cloud Masking', 'NDVI & NDWI Stack', 'Automated Inference'],
      icon: Cpu,
    },
    {
      stepNumber: 'Step 03',
      title: 'Real-World Evaluation',
      description:
        'Officials use these insights to assess flood inundation, track unauthorized urbanization, and evaluate seasonal crop health.',
      badgeText: 'Administrative Action',
      highlights: ['Flood Assessment', 'Urban Encroachment', 'Crop Health'],
      icon: ClipboardCheck,
    },
  ];

  const coreModules = [
    {
      id: 'analytics',
      options: { initialTab: 'lulc' },
      code: 'Module 01',
      title: 'AI Land Cover (LULC)',
      description:
        'Hectare analytics, spatial statistics, and terrain breakdowns across verified village boundaries.',
      actionLabel: 'Open LULC Analytics',
      icon: Layers,
      previewTags: [
        { label: 'Cropland', color: 'bg-[#4A7C59]' },
        { label: 'Trees', color: 'bg-[#2E5238]' },
        { label: 'Built-Up', color: 'bg-[#B35C44]' },
        { label: 'Water', color: 'bg-[#3D6E8A]' },
      ],
    },
    {
      id: 'gis',
      options: {},
      code: 'Module 02',
      title: 'GIS Spatial Explorer',
      description:
        'Interactive metric grid viewer with transparent spectral index overlays (NDWI, SAVI, MNDWI).',
      actionLabel: 'Launch Spatial Explorer',
      icon: Map,
      previewTags: [
        { label: 'NDWI Layer', color: 'bg-[#3D6E8A]' },
        { label: 'SAVI Arid', color: 'bg-[#C4A661]' },
        { label: 'MNDWI Mask', color: 'bg-[#5B8A68]' },
      ],
    },
    {
      id: 'change',
      options: {},
      code: 'Module 03',
      title: 'Temporal Change Engine',
      description:
        'Dual-date inference to map environmental transitions over time across seasonal and annual epochs.',
      actionLabel: 'Inspect Temporal Change',
      icon: GitCompare,
      previewTags: [
        { label: 'Epoch T₁ Baseline', color: 'bg-stone-500' },
        { label: 'Epoch T₂ Target', color: 'bg-emerald-700' },
        { label: 'Δ Surface Audit', color: 'bg-[#A67C2E]' },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-[#F7F5F0] text-[#2C2A29] font-sans antialiased flex flex-col">
      {/* ── 1. Top Navigation Header ── */}
      <header className="sticky top-0 z-40 bg-white border-b border-[#E2DAC6] shadow-[0_1px_2px_rgba(44,42,41,0.05)]">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-4 flex flex-wrap items-center justify-between gap-4">
          {/* Gram Darpan Logo & Title */}
          <a
            href="#overview"
            className="flex items-center gap-3.5 text-[#2C2A29] no-underline rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-700"
          >
            <div className="w-11 h-11 rounded-md bg-emerald-700 border border-emerald-800 text-white flex items-center justify-center shrink-0">
              <Landmark className="w-5 h-5" aria-hidden="true" />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-serif font-bold tracking-tight text-[#2C2A29] leading-tight">
                Gram Darpan
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-stone-600">
                WebGIS Satellite Governance Portal
              </span>
            </div>
          </a>

          {/* Anchor Links + Prominent Solid Green Open Dashboard Button */}
          <nav
            aria-label="Primary Header Navigation"
            className="flex flex-wrap items-center gap-2 sm:gap-6"
          >
            <a
              href="#overview"
              className="inline-flex items-center gap-2 px-3 py-2 text-sm sm:text-base font-semibold text-[#2C2A29] hover:text-emerald-700 transition-colors"
            >
              <Compass className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Overview</span>
            </a>

            <a
              href="#process"
              className="inline-flex items-center gap-2 px-3 py-2 text-sm sm:text-base font-semibold text-[#2C2A29] hover:text-emerald-700 transition-colors"
            >
              <Workflow className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Process</span>
            </a>

            <a
              href="#modules"
              className="inline-flex items-center gap-2 px-3 py-2 text-sm sm:text-base font-semibold text-[#2C2A29] hover:text-emerald-700 transition-colors"
            >
              <Grid className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Modules</span>
            </a>

            <button
              type="button"
              onClick={onOpenDashboard}
              className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-md bg-emerald-700 hover:bg-emerald-800 text-white text-sm sm:text-base font-semibold border border-emerald-800 shadow-[0_1px_2px_rgba(44,42,41,0.12)] transition-colors cursor-pointer"
            >
              <LayoutDashboard className="w-4 h-4" aria-hidden="true" />
              <span>Open Dashboard</span>
            </button>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* ── 2. Hero Section (Objective & Agricultural Parcel Atlas Visual) ── */}
        <section
          id="overview"
          className="relative overflow-hidden border-b border-[#E2DAC6] bg-[#F7F5F0] py-16 lg:py-22"
          style={{
            backgroundImage:
              'linear-gradient(to right, rgba(226, 218, 198, 0.45) 1px, transparent 1px), linear-gradient(to bottom, rgba(226, 218, 198, 0.45) 1px, transparent 1px)',
            backgroundSize: '44px 44px',
          }}
        >
          <div className="max-w-7xl mx-auto px-6 lg:px-10">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-10 items-center">
              {/* Left Column: Authoritative Editorial Copy */}
              <div className="lg:col-span-6 space-y-6">
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-white border border-[#E2DAC6] rounded-md text-sm font-semibold text-emerald-800 shadow-[0_1px_2px_rgba(44,42,41,0.05)]">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                  <span>Official Rural Spatial Observatory</span>
                </div>

                <h1 className="font-serif text-4xl sm:text-5xl font-bold tracking-tight text-[#2C2A29] leading-[1.12]">
                  Precision spatial intelligence for sustainable rural governance.
                </h1>

                <p className="text-lg text-stone-700 leading-relaxed max-w-xl">
                  Gram Darpan merges multi-modal Sentinel-1 radar and Sentinel-2 optical satellite imagery with automated Random Forest AI to monitor land use, watershed reserves, and seasonal environmental changes across every village jurisdiction.
                </p>

                <div className="flex flex-wrap items-center gap-4 pt-2">
                  <button
                    type="button"
                    onClick={onOpenDashboard}
                    className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-md bg-emerald-700 hover:bg-emerald-800 text-white text-base font-semibold border border-emerald-800 shadow-[0_2px_4px_rgba(44,42,41,0.14)] transition-colors cursor-pointer"
                  >
                    <LayoutDashboard className="w-5 h-5" aria-hidden="true" />
                    <span>Open Dashboard</span>
                    <ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </button>

                  <a
                    href="#process"
                    className="inline-flex items-center gap-2 px-6 py-3.5 rounded-md bg-white hover:bg-stone-100 text-[#2C2A29] text-base font-semibold border border-[#E2DAC6] shadow-[0_1px_2px_rgba(44,42,41,0.05)] transition-colors"
                  >
                    <Workflow className="w-5 h-5 text-emerald-700" aria-hidden="true" />
                    <span>See How It Works</span>
                  </a>
                </div>

                {/* Grounded Atlas Telemetry Strip */}
                <div className="pt-4 grid grid-cols-3 gap-4 max-w-lg">
                  <div className="bg-white border border-[#E2DAC6] rounded-md px-4 py-3 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                    <span className="text-xs font-semibold uppercase tracking-wide text-stone-600 block">
                      Resolution
                    </span>
                    <span className="text-lg font-bold font-mono text-[#2C2A29]">10m &times; 10m</span>
                  </div>
                  <div className="bg-white border border-[#E2DAC6] rounded-md px-4 py-3 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                    <span className="text-xs font-semibold uppercase tracking-wide text-stone-600 block">
                      Villages
                    </span>
                    <span className="text-lg font-bold font-mono text-[#2C2A29]">
                      {villageCount > 0 ? villageCount : 'PostGIS'}
                    </span>
                  </div>
                  <div className="bg-white border border-[#E2DAC6] rounded-md px-4 py-3 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                    <span className="text-xs font-semibold uppercase tracking-wide text-stone-600 block">
                      Acquisitions
                    </span>
                    <span className="text-lg font-bold font-mono text-emerald-800">
                      {sceneCount > 0 ? `${sceneCount} Scenes` : isConnected ? 'Live API' : 'Ready'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Right Column: Agricultural Map Visual Cluster & Floating Metric Cards */}
              <div className="lg:col-span-6 relative px-2 sm:px-6 py-6">
                {/* Outer Survey Concentric Rings Frame (Atlas Motif) */}
                <div className="relative mx-auto max-w-lg bg-white border border-[#E2DAC6] rounded-xl p-5 sm:p-6 shadow-[0_4px_14px_rgba(44,42,41,0.08)]">
                  {/* Top Atlas Plate Header */}
                  <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-[#EDE7D9]">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-stone-600">
                      <MapPin className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                      <span>Cadastral Plate · Sample AOI</span>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#F7F5F0] border border-[#E2DAC6] rounded-sm text-xs font-mono font-semibold text-[#2C2A29]">
                      <Compass className="w-3.5 h-3.5 text-emerald-700" aria-hidden="true" />
                      <span>26.91°N 75.79°E</span>
                    </span>
                  </div>

                  {/* Agricultural Land Plots Collage */}
                  <div className="relative bg-[#F7F5F0] border border-[#E2DAC6] rounded-lg p-4">
                    {/* Cadastral Boundary Shape Container */}
                    <div className="relative grid grid-cols-12 grid-rows-6 gap-2 h-80 sm:h-96 p-2 bg-[#FAF8F4] border-2 border-[#36533E] rounded-[28px] overflow-hidden">
                      {/* Plot 1: Deep Irrigated Cropland */}
                      <div className="col-span-5 row-span-3 bg-[#3E6B48] border border-[#FAF8F4] rounded-tl-[20px] p-2.5 flex items-end">
                        <span className="text-[11px] font-mono font-semibold text-white/90">
                          PLOT A-01
                        </span>
                      </div>

                      {/* Plot 2: Young Rabi Crop (Olive Sage) */}
                      <div className="col-span-4 row-span-2 bg-[#719358] border border-[#FAF8F4] p-2">
                        <span className="text-[11px] font-mono font-semibold text-white/90">
                          PLOT A-02
                        </span>
                      </div>

                      {/* Plot 3: Sandy Fallow Soil */}
                      <div className="col-span-3 row-span-2 bg-[#C8AC70] border border-[#FAF8F4] rounded-tr-[20px] p-2">
                        <span className="text-[11px] font-mono font-semibold text-[#2C2A29]">
                          B-04
                        </span>
                      </div>

                      {/* Plot 4: Pivot Cropland Highlight */}
                      <div className="col-span-4 row-span-2 bg-[#D3BA7A] border border-[#FAF8F4] flex items-center justify-center relative">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-[#688D4E] border-2 border-[#FAF8F4] flex items-center justify-center">
                          <span className="text-[10px] font-mono font-bold text-white">PIVOT</span>
                        </div>
                      </div>

                      {/* Plot 5: Dense Agro-Forestry / Trees */}
                      <div className="col-span-3 row-span-2 bg-[#56814F] border border-[#FAF8F4] p-2">
                        <span className="text-[11px] font-mono font-semibold text-white/90">
                          B-07
                        </span>
                      </div>

                      {/* Plot 6: Harvested Earth Parcel with Orchard Circle */}
                      <div className="col-span-5 row-span-3 bg-[#7D6648] border border-[#FAF8F4] rounded-bl-[20px] flex items-center justify-center relative">
                        <div className="w-16 h-16 rounded-full bg-[#44714A] border-2 border-[#FAF8F4] flex items-center justify-center">
                          <Trees className="w-5 h-5 text-white" aria-hidden="true" />
                        </div>
                      </div>

                      {/* Plot 7: Dense Cropland Southern Sector */}
                      <div className="col-span-4 row-span-2 bg-[#3F6D4A] border border-[#FAF8F4] p-2.5 flex items-end">
                        <span className="text-[11px] font-mono font-semibold text-white/90">
                          PLOT C-11
                        </span>
                      </div>

                      {/* Plot 8: Check Dam / Moisture Reserve */}
                      <div className="col-span-3 row-span-2 bg-[#93AD8B] border border-[#FAF8F4] rounded-br-[20px] p-2 flex items-end justify-end">
                        <span className="text-[11px] font-mono font-semibold text-[#2C2A29]">
                          C-14
                        </span>
                      </div>

                      {/* Crisp Rural Stream / Irrigation Canal Overlay */}
                      <svg
                        viewBox="0 0 400 120"
                        className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 w-full h-24 opacity-85"
                        aria-hidden="true"
                      >
                        <path
                          d="M -10 72 C 75 52, 130 92, 215 62 C 285 38, 340 54, 410 42"
                          fill="none"
                          stroke="#ECE8DC"
                          strokeWidth="7"
                          strokeLinecap="round"
                        />
                        <path
                          d="M -10 72 C 75 52, 130 92, 215 62 C 285 38, 340 54, 410 42"
                          fill="none"
                          stroke="#5B859B"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeDasharray="6 4"
                        />
                      </svg>
                    </div>

                    {/* Floating Data Card 1: Top-Left (NDVI: 0.61) */}
                    <div className="sm:absolute sm:-top-5 sm:-left-5 mt-3 sm:mt-0 bg-white border border-[#E2DAC6] rounded-lg px-4 py-3 shadow-[0_4px_10px_rgba(44,42,41,0.10)] flex items-center gap-3 z-20">
                      <span className="w-9 h-9 rounded-md bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
                        <Leaf className="w-4 h-4" aria-hidden="true" />
                      </span>
                      <div>
                        <span className="text-xs font-semibold text-stone-600 block leading-tight">
                          Vegetation Health
                        </span>
                        <span className="text-base font-bold font-mono text-[#2C2A29]">
                          NDVI: 0.61
                        </span>
                      </div>
                    </div>

                    {/* Floating Data Card 2: Middle-Right (Rainfall: 42mm) */}
                    <div className="sm:absolute sm:top-1/2 sm:-translate-y-1/2 sm:-right-6 mt-2.5 sm:mt-0 bg-white border border-[#E2DAC6] rounded-lg px-4 py-3 shadow-[0_4px_10px_rgba(44,42,41,0.10)] flex items-center gap-3 z-20">
                      <span className="w-9 h-9 rounded-md bg-[#EEF4F7] border border-[#BACEDB] flex items-center justify-center text-[#346078] shrink-0">
                        <CloudRain className="w-4 h-4" aria-hidden="true" />
                      </span>
                      <div>
                        <span className="text-xs font-semibold text-stone-600 block leading-tight">
                          30-Day Precipitation
                        </span>
                        <span className="text-base font-bold font-mono text-[#2C2A29]">
                          Rainfall: 42mm
                        </span>
                      </div>
                    </div>

                    {/* Floating Data Card 3: Bottom-Left (AI Classification: Cropland) */}
                    <div className="sm:absolute sm:-bottom-5 sm:left-4 mt-2.5 sm:mt-0 bg-white border border-[#E2DAC6] rounded-lg px-4 py-3 shadow-[0_4px_10px_rgba(44,42,41,0.10)] flex items-center gap-3 z-20">
                      <span className="w-9 h-9 rounded-md bg-[#FAF3E3] border border-[#E2CFA3] flex items-center justify-center text-[#8F641B] shrink-0">
                        <Wheat className="w-4 h-4" aria-hidden="true" />
                      </span>
                      <div>
                        <span className="text-xs font-semibold text-stone-600 block leading-tight">
                          Random Forest Model
                        </span>
                        <span className="text-sm sm:text-base font-bold text-[#2C2A29]">
                          AI Classification: <span className="text-emerald-700">Cropland</span>
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Plate Cartographic Symbology Key */}
                  <div className="mt-8 pt-3.5 border-t border-[#EDE7D9] flex flex-wrap items-center justify-between gap-3 text-xs font-semibold text-stone-600">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-xs bg-[#3E6B48] border border-[#2C2A29]/20" />
                      <span>Cropland</span>
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-xs bg-[#56814F] border border-[#2C2A29]/20" />
                      <span>Tree Cover</span>
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-xs bg-[#C8AC70] border border-[#2C2A29]/20" />
                      <span>Sandy Fallow</span>
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-xs bg-[#5B859B] border border-[#2C2A29]/20" />
                      <span>Surface Water</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── 3. Workflow & Real-Life Application (Horizontal Process Flow) ── */}
        <section
          id="process"
          aria-labelledby="process-heading"
          className="py-16 lg:py-20 bg-white border-b border-[#E2DAC6]"
        >
          <div className="max-w-7xl mx-auto px-6 lg:px-10">
            <div className="pb-5 mb-12 border-b-2 border-[#E2DAC6] flex flex-wrap items-end justify-between gap-4">
              <div>
                <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-700 mb-1.5">
                  <Workflow className="w-4 h-4" aria-hidden="true" />
                  <span>Operational Process</span>
                </span>
                <h2
                  id="process-heading"
                  className="font-serif text-3xl sm:text-4xl font-bold text-[#2C2A29]"
                >
                  From Satellite Pass to Village Decision
                </h2>
              </div>
              <p className="text-base text-stone-600 max-w-xl">
                A deterministic three-stage remote sensing pipeline built for rapid administrative evaluation at the panchayat and district level.
              </p>
            </div>

            {/* Horizontal 3-Step Flow */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8 relative">
              {processSteps.map((step, index) => {
                const StepIcon = step.icon;
                return (
                  <article
                    key={step.stepNumber}
                    className="relative bg-[#F7F5F0] border border-[#E2DAC6] rounded-lg p-7 flex flex-col justify-between gap-6 shadow-[0_1px_2px_rgba(44,42,41,0.04)]"
                  >
                    <div className="space-y-4">
                      {/* Step Header Row */}
                      <div className="flex items-center justify-between gap-3 pb-3.5 border-b border-[#E2DAC6]">
                        <div className="flex items-center gap-3">
                          <span className="w-10 h-10 rounded-md bg-white border border-[#E2DAC6] flex items-center justify-center text-emerald-700 shrink-0 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                            <StepIcon className="w-5 h-5" aria-hidden="true" />
                          </span>
                          <div>
                            <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 block">
                              {step.stepNumber}
                            </span>
                            <h3 className="text-xl font-bold text-[#2C2A29] leading-tight">
                              {step.title}
                            </h3>
                          </div>
                        </div>

                        {index < processSteps.length - 1 && (
                          <span className="hidden lg:inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-white border border-[#E2DAC6] px-2 py-1 rounded-sm">
                            <span>Next</span>
                            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                          </span>
                        )}
                      </div>

                      <p className="text-base text-stone-700 leading-relaxed">
                        {step.description}
                      </p>
                    </div>

                    {/* Stage Spec Badges */}
                    <div className="pt-4 border-t border-[#E2DAC6] flex flex-wrap items-center gap-2">
                      {step.highlights.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white border border-[#E2DAC6] rounded-sm text-xs font-semibold text-[#2C2A29]"
                        >
                          <CheckCircle2 className="w-3 h-3 text-emerald-700" aria-hidden="true" />
                          <span>{tag}</span>
                        </span>
                      ))}
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── 4. Core Features (The Interactive Modules Grid) ── */}
        <section
          id="modules"
          aria-labelledby="modules-heading"
          className="py-16 lg:py-20 bg-[#F7F5F0]"
        >
          <div className="max-w-7xl mx-auto px-6 lg:px-10">
            <div className="pb-5 mb-12 border-b-2 border-[#E2DAC6] flex flex-wrap items-end justify-between gap-4">
              <div>
                <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-700 mb-1.5">
                  <Grid className="w-4 h-4" aria-hidden="true" />
                  <span>Core Capabilities</span>
                </span>
                <h2
                  id="modules-heading"
                  className="font-serif text-3xl sm:text-4xl font-bold text-[#2C2A29]"
                >
                  Integrated Analytical Modules
                </h2>
              </div>
              <p className="text-base text-stone-600 max-w-xl">
                Launch any specialized module below to inspect calibrated land-cover rasters, spectral indices, or multi-date transitions.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-7">
              {coreModules.map((mod) => {
                const Icon = mod.icon;
                return (
                  <button
                    key={mod.id}
                    type="button"
                    onClick={() => onNavigateModule(mod.id, mod.options)}
                    className="group text-left bg-white border border-[#E2DAC6] hover:border-emerald-700 rounded-lg p-7 shadow-[0_1px_3px_rgba(44,42,41,0.06)] hover:shadow-[0_4px_12px_rgba(44,42,41,0.09)] transition-all flex flex-col justify-between gap-6 cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-700"
                  >
                    <div className="space-y-4">
                      {/* Card Header */}
                      <div className="flex items-center justify-between gap-3 pb-3.5 border-b border-[#EDE7D9]">
                        <div className="inline-flex items-center gap-2.5 text-emerald-800 font-bold text-sm">
                          <span className="w-10 h-10 rounded-md bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
                            <Icon className="w-5 h-5" aria-hidden="true" />
                          </span>
                          <span>{mod.code}</span>
                        </div>
                        <span className="text-xs font-semibold uppercase tracking-wide text-stone-600">
                          Interactive
                        </span>
                      </div>

                      {/* Title & Description */}
                      <div>
                        <h3 className="text-xl font-bold text-[#2C2A29] group-hover:text-emerald-800 transition-colors">
                          {mod.title}
                        </h3>
                        <p className="mt-2.5 text-base text-stone-700 leading-relaxed">
                          {mod.description}
                        </p>
                      </div>

                      {/* Minimalist Swatch / Tag Row */}
                      <div className="flex flex-wrap gap-2 pt-1">
                        {mod.previewTags.map((tag) => (
                          <span
                            key={tag.label}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#FAF8F4] border border-[#E2DAC6] rounded-sm text-xs font-semibold text-[#2C2A29]"
                          >
                            <span className={`w-2.5 h-2.5 rounded-xs ${tag.color}`} aria-hidden="true" />
                            <span>{tag.label}</span>
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Explicit Action Row */}
                    <div className="pt-4 border-t border-[#EDE7D9] w-full flex items-center justify-between">
                      <span className="inline-flex items-center gap-2 text-base font-bold text-emerald-700 group-hover:text-emerald-800">
                        <span>{mod.actionLabel}</span>
                        <ArrowRight
                          className="w-4 h-4 transition-transform group-hover:translate-x-1"
                          aria-hidden="true"
                        />
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Secondary Institutional Land-Class Reference Bar */}
            <div className="mt-12 bg-white border border-[#E2DAC6] rounded-lg p-7 flex flex-wrap items-center justify-between gap-6 shadow-[0_1px_2px_rgba(44,42,41,0.05)]">
              <div className="space-y-2 max-w-2xl">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 block">
                  Field-Ready Governance Outputs
                </span>
                <h3 className="text-xl font-bold text-[#2C2A29]">
                  Access full village boundaries, hectare tables, and spectral plates.
                </h3>
                <div className="flex flex-wrap items-center gap-4 pt-1 text-sm font-medium text-stone-700">
                  <span className="inline-flex items-center gap-1.5">
                    <Wheat className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                    <span>Cropland Monitoring</span>
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Waves className="w-4 h-4 text-[#346078]" aria-hidden="true" />
                    <span>Water Bodies &amp; Floods</span>
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Home className="w-4 h-4 text-[#8F641B]" aria-hidden="true" />
                    <span>Settlement Growth</span>
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Calendar className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                    <span>Seasonal Audits</span>
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={onOpenDashboard}
                className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-md bg-emerald-700 hover:bg-emerald-800 text-white text-base font-semibold border border-emerald-800 shadow-[0_1px_2px_rgba(44,42,41,0.12)] transition-colors cursor-pointer"
              >
                <LayoutDashboard className="w-5 h-5" aria-hidden="true" />
                <span>Open Dashboard</span>
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* ── Institutional Atlas Footer ── */}
      <footer className="bg-white border-t border-[#E2DAC6] py-8">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 flex flex-wrap items-center justify-between gap-4 text-sm text-stone-600">
          <div className="flex items-center gap-2.5 font-semibold text-[#2C2A29]">
            <Landmark className="w-4 h-4 text-emerald-700" aria-hidden="true" />
            <span>Gram Darpan &mdash; Spatial Intelligence Portal for Rural Governance</span>
          </div>

          <div className="flex flex-wrap items-center gap-6">
            <a href="#overview" className="inline-flex items-center gap-1.5 hover:text-emerald-700 font-medium">
              <Compass className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Overview</span>
            </a>
            <a href="#process" className="inline-flex items-center gap-1.5 hover:text-emerald-700 font-medium">
              <Workflow className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Process</span>
            </a>
            <a href="#modules" className="inline-flex items-center gap-1.5 hover:text-emerald-700 font-medium">
              <Grid className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Modules</span>
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
