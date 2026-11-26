import React, { useState, useEffect, useCallback } from 'react';
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
  Grid,
  Wheat,
  Waves,
  CheckCircle2,
  Workflow,
  Calendar,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

/**
 * Gram Darpan — Official Spatial Intelligence Portal for Rural Governance
 * Aesthetic: High-end Printed Atlas meets Interactive GIS Tool (Strictly Light Mode)
 */
export function LandingPage({
  onOpenDashboard = () => {},
  onNavigateModule = () => {},
  villageCount = 0,
  sceneCount = 0,
  isConnected = true,
}) {
  /* ── Satellite Imagery Carousel ── */
  const carouselSlides = [
    {
      src: '/images/slider-1.jpg',
      alt: 'High-resolution satellite terrain mosaic — agricultural parcels and settlement clusters',
      caption: 'Satellite Terrain Mosaic',
      detail: 'Sentinel-2 True-Color Composite · 10m Resolution',
      needsCrop: true,
    },
    {
      src: '/images/slider-2.webp',
      alt: 'Thermal infrared land surface temperature overlay across agricultural fields',
      caption: 'Thermal Surface Analysis',
      detail: 'Land Surface Temperature · Infrared Band Composite',
      needsCrop: false,
    },
    {
      src: '/images/slider-3.jpg',
      alt: '3D hydrological terrain model with flood contour mapping',
      caption: 'Hydrological Contour Model',
      detail: '3D Terrain Elevation · Flood Risk Delineation',
      needsCrop: false,
    },
    {
      src: '/images/slider-4.jpg',
      alt: 'NDVI crop health classification overlay on agricultural parcels',
      caption: 'NDVI Crop Health Index',
      detail: 'Vegetation Vigor Classification · Random Forest AI',
      needsCrop: false,
    },
  ];

  const [activeSlide, setActiveSlide] = useState(0);

  const goToSlide = useCallback(
    (index) => {
      setActiveSlide((index + carouselSlides.length) % carouselSlides.length);
    },
    [carouselSlides.length],
  );

  const goNext = useCallback(() => goToSlide(activeSlide + 1), [activeSlide, goToSlide]);
  const goPrev = useCallback(() => goToSlide(activeSlide - 1), [activeSlide, goToSlide]);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveSlide((prev) => (prev + 1) % carouselSlides.length);
    }, 4500);
    return () => clearInterval(timer);
  }, [carouselSlides.length]);

  const processSteps = [
    {
      stepNumber: 'Step 01',
      title: 'Select & Acquire',
      description:
        'Choose a village jurisdiction. The system automatically fetches 10m-resolution Sentinel-1 (Radar) and Sentinel-2 (Optical) data.',
      highlights: ['Village Boundary AOI', 'Sentinel-1 SAR', 'Sentinel-2 L2A'],
      icon: Satellite,
    },
    {
      stepNumber: 'Step 02',
      title: 'AI Processing',
      description:
        'Navigate to the Analytics Engine where our Random Forest model classifies pixels into Cropland, Trees, Water, and Settlements.',
      highlights: ['SCL Cloud Masking', '6-Feature Matrix', '100 m² Cell Grid'],
      icon: Cpu,
    },
    {
      stepNumber: 'Step 03',
      title: 'Real-World Evaluation',
      description:
        'Officials use these insights to assess flood inundation, track unauthorized urbanization, and evaluate seasonal crop health.',
      highlights: ['Flood Inundation', 'Urbanization Audit', 'Crop Health'],
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
        'Hectare analytics, spatial statistics, and terrain breakdowns across registered village jurisdictions.',
      actionLabel: 'Open LULC Analytics',
      icon: Layers,
      specs: ['Cropland & Canopy Area', 'Built-Up Expansion', '10m Hectare Ledger'],
    },
    {
      id: 'gis',
      options: {},
      code: 'Module 02',
      title: 'GIS Spatial Explorer',
      description:
        'Interactive metric grid viewer with transparent spectral index overlays (NDWI, SAVI, MNDWI).',
      actionLabel: 'Open Spatial Explorer',
      icon: Map,
      specs: ['PostGIS Boundaries', 'NDWI · SAVI · MNDWI', 'Multi-Basemap Viewer'],
    },
    {
      id: 'change',
      options: {},
      code: 'Module 03',
      title: 'Temporal Change Engine',
      description:
        'Dual-date inference to map environmental transitions over time across seasonal and annual epochs.',
      actionLabel: 'Open Temporal Change',
      icon: GitCompare,
      specs: ['T₁ vs T₂ Comparison', 'Δ NDVI Vegetation Shift', 'Δ NDWI Water Shift'],
    },
  ];

  return (
    <div className="min-h-screen bg-[#F7F5F0] text-[#2C2A29] font-sans antialiased flex flex-col">
      {/* ── 1. Top Navigation Header ── */}
      <header className="sticky top-0 z-40 bg-white border-b border-[#E2DAC6] shadow-[0_1px_2px_rgba(44,42,41,0.05)]">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-4 flex flex-wrap items-center justify-between gap-4">
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
                Rural Spatial Intelligence Portal
              </span>
            </div>
          </a>

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
        {/* ── 2. Hero Section (Objective & Interactive Observation Dossier) ── */}
        <section
          id="overview"
          className="border-b border-[#E2DAC6] bg-[#F7F5F0] py-16 lg:py-22"
        >
          <div className="max-w-7xl mx-auto px-6 lg:px-10">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
              {/* Left Column: Authoritative Serif Objective & Actions */}
              <div className="lg:col-span-6 space-y-6">
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-white border border-[#E2DAC6] rounded-md text-sm font-semibold text-emerald-800 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                  <span>Decision Support Portal &middot; Sentinel &amp; Random Forest AI</span>
                </div>

                <h1 className="font-serif text-4xl sm:text-5xl font-bold tracking-tight text-[#2C2A29] leading-[1.12]">
                  Precision spatial intelligence for sustainable rural governance.
                </h1>

                <p className="text-lg text-stone-700 leading-relaxed max-w-xl">
                  Gram Darpan merges multi-modal Sentinel-1 radar and Sentinel-2 optical satellite imagery with automated Random Forest AI to deliver verified 10-meter land use classification, hydrological indicators, and environmental change assessments.
                </p>

                <div className="flex flex-wrap items-center gap-4 pt-2">
                  <button
                    type="button"
                    onClick={onOpenDashboard}
                    className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-md bg-emerald-700 hover:bg-emerald-800 text-white text-base font-semibold border border-emerald-800 shadow-[0_2px_4px_rgba(44,42,41,0.12)] transition-colors cursor-pointer"
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
                    <span>Explore Workflow</span>
                  </a>
                </div>

                {/* Printed-Atlas System Ledger Strip */}
                <div className="pt-4 grid grid-cols-3 gap-4 max-w-lg">
                  <div className="bg-white border border-[#E2DAC6] rounded-md px-4 py-3.5 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                    <span className="text-xs font-semibold uppercase tracking-wide text-stone-600 block">
                      Grid Scale
                    </span>
                    <span className="text-lg font-bold font-mono text-[#2C2A29]">10m &times; 10m</span>
                  </div>
                  <div className="bg-white border border-[#E2DAC6] rounded-md px-4 py-3.5 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                    <span className="text-xs font-semibold uppercase tracking-wide text-stone-600 block">
                      Jurisdictions
                    </span>
                    <span className="text-lg font-bold font-mono text-[#2C2A29]">
                      {villageCount > 0 ? `${villageCount} Units` : 'PostGIS'}
                    </span>
                  </div>
                  <div className="bg-white border border-[#E2DAC6] rounded-md px-4 py-3.5 shadow-[0_1px_2px_rgba(44,42,41,0.04)]">
                    <span className="text-xs font-semibold uppercase tracking-wide text-stone-600 block">
                      Observations
                    </span>
                    <span className="text-lg font-bold font-mono text-emerald-800">
                      {sceneCount > 0 ? `${sceneCount} Scenes` : isConnected ? 'Active' : 'Ready'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Right Column: Satellite Imagery Carousel */}
              <div className="lg:col-span-6 flex flex-col">
                <div className="relative border border-[#E2DAC6] rounded-lg shadow-[0_3px_10px_rgba(44,42,41,0.07)] overflow-hidden bg-[#F7F5F0]">
                  {/* Image Viewport */}
                  <div className="relative h-[280px] sm:h-[340px] lg:h-[380px] w-full overflow-hidden">
                    {carouselSlides.map((slide, index) => (
                      <div
                        key={slide.src}
                        className={`absolute inset-0 w-full h-full transition-opacity duration-700 ease-in-out ${
                          index === activeSlide ? 'opacity-100 z-10' : 'opacity-0 z-0'
                        }`}
                        aria-hidden={index !== activeSlide}
                      >
                        <img
                          src={slide.src}
                          alt={slide.alt}
                          loading={index === 0 ? 'eager' : 'lazy'}
                          className={`w-full h-full object-cover ${
                            slide.needsCrop ? 'scale-[1.15] origin-center' : ''
                          }`}
                        />
                      </div>
                    ))}

                    {/* Prev / Next Arrow Buttons */}
                    <button
                      type="button"
                      onClick={goPrev}
                      aria-label="Previous slide"
                      className="absolute left-2.5 top-1/2 -translate-y-1/2 z-20 w-9 h-9 rounded-md bg-white/85 border border-[#E2DAC6] flex items-center justify-center text-[#2C2A29] hover:bg-white hover:border-emerald-700 transition-colors cursor-pointer shadow-[0_1px_3px_rgba(44,42,41,0.1)]"
                    >
                      <ChevronLeft className="w-4.5 h-4.5" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={goNext}
                      aria-label="Next slide"
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 z-20 w-9 h-9 rounded-md bg-white/85 border border-[#E2DAC6] flex items-center justify-center text-[#2C2A29] hover:bg-white hover:border-emerald-700 transition-colors cursor-pointer shadow-[0_1px_3px_rgba(44,42,41,0.1)]"
                    >
                      <ChevronRight className="w-4.5 h-4.5" aria-hidden="true" />
                    </button>

                    {/* Navigation Dots */}
                    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2">
                      {carouselSlides.map((slide, index) => (
                        <button
                          key={slide.src}
                          type="button"
                          onClick={() => goToSlide(index)}
                          aria-label={`Go to slide ${index + 1}: ${slide.caption}`}
                          aria-current={index === activeSlide ? 'true' : undefined}
                          className={`rounded-full transition-all duration-300 cursor-pointer border ${
                            index === activeSlide
                              ? 'w-6 h-2 bg-emerald-700 border-emerald-800'
                              : 'w-2 h-2 bg-white/80 border-stone-300 hover:bg-white hover:border-emerald-600'
                          }`}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Caption Bar */}
                  <div className="px-4 py-3 bg-white border-t border-[#E2DAC6] flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="w-7 h-7 rounded-md bg-emerald-50 border border-emerald-200 flex items-center justify-center shrink-0">
                        <Satellite className="w-3.5 h-3.5 text-emerald-700" aria-hidden="true" />
                      </span>
                      <div className="min-w-0">
                        <span className="text-sm font-bold text-[#2C2A29] block leading-tight truncate">
                          {carouselSlides[activeSlide].caption}
                        </span>
                        <span className="text-xs text-stone-600 truncate block">
                          {carouselSlides[activeSlide].detail}
                        </span>
                      </div>
                    </div>
                    <span className="text-xs font-mono font-semibold text-stone-500 bg-[#FAF8F4] border border-[#E2DAC6] px-2 py-0.5 rounded-sm shrink-0">
                      {activeSlide + 1}/{carouselSlides.length}
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
                  <span>How It Works</span>
                </span>
                <h2
                  id="process-heading"
                  className="font-serif text-3xl sm:text-4xl font-bold text-[#2C2A29]"
                >
                  Operational Process &amp; Governance Impact
                </h2>
              </div>
              <p className="text-base text-stone-600 max-w-xl">
                Three structured steps take officials from multi-sensor satellite acquisition to verified village field assessments.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
              {processSteps.map((step, index) => {
                const StepIcon = step.icon;
                return (
                  <article
                    key={step.stepNumber}
                    className="bg-[#F7F5F0] border border-[#E2DAC6] rounded-lg p-7 flex flex-col justify-between gap-6 shadow-[0_1px_2px_rgba(44,42,41,0.04)]"
                  >
                    <div className="space-y-4">
                      <div className="flex items-center justify-between gap-3 pb-4 border-b border-[#E2DAC6]">
                        <div className="flex items-center gap-3">
                          <span className="w-10 h-10 rounded-md bg-white border border-[#E2DAC6] flex items-center justify-center text-emerald-700 shrink-0">
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
                          <span className="hidden lg:inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-white border border-[#E2DAC6] px-2.5 py-1 rounded-sm">
                            <span>Next</span>
                            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                          </span>
                        )}
                      </div>

                      <p className="text-base text-stone-700 leading-relaxed">
                        {step.description}
                      </p>
                    </div>

                    <div className="pt-4 border-t border-[#E2DAC6] flex flex-wrap gap-2">
                      {step.highlights.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white border border-[#E2DAC6] rounded-sm text-xs font-semibold text-[#2C2A29]"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" aria-hidden="true" />
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
                  <span>Core Features</span>
                </span>
                <h2
                  id="modules-heading"
                  className="font-serif text-3xl sm:text-4xl font-bold text-[#2C2A29]"
                >
                  Analytical Portal Modules
                </h2>
              </div>
              <p className="text-base text-stone-600 max-w-xl">
                Select any workspace module below to inspect calibrated land-cover reports, spectral map layers, or temporal change detection.
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
                      <div className="flex items-center justify-between gap-3 pb-3.5 border-b border-[#EDE7D9]">
                        <div className="inline-flex items-center gap-2.5 text-emerald-800 font-bold text-sm">
                          <span className="w-10 h-10 rounded-md bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
                            <Icon className="w-5 h-5" aria-hidden="true" />
                          </span>
                          <span>{mod.code}</span>
                        </div>
                        <span className="text-xs font-semibold uppercase tracking-wide text-stone-600">
                          Workspace
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

                      <div className="flex flex-wrap gap-2 pt-1">
                        {mod.specs.map((spec) => (
                          <span
                            key={spec}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#FAF8F4] border border-[#E2DAC6] rounded-sm text-xs font-semibold text-[#2C2A29]"
                          >
                            <CheckCircle2 className="w-3 h-3 text-emerald-700" aria-hidden="true" />
                            <span>{spec}</span>
                          </span>
                        ))}
                      </div>
                    </div>

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

            {/* Bottom Callout Strip */}
            <div className="mt-12 bg-white border border-[#E2DAC6] rounded-lg p-7 flex flex-wrap items-center justify-between gap-6 shadow-[0_1px_2px_rgba(44,42,41,0.05)]">
              <div className="space-y-2 max-w-2xl">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 block">
                  Institutional Verification Portal
                </span>
                <h3 className="text-xl font-bold text-[#2C2A29]">
                  Launch the full WebGIS command center for live village assessments.
                </h3>
                <div className="flex flex-wrap items-center gap-4 pt-1 text-sm font-medium text-stone-700">
                  <span className="inline-flex items-center gap-1.5">
                    <Wheat className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                    <span>Seasonal Crop Audits</span>
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Waves className="w-4 h-4 text-[#346078]" aria-hidden="true" />
                    <span>Watershed Storage</span>
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Calendar className="w-4 h-4 text-[#8F641B]" aria-hidden="true" />
                    <span>Multi-Date History</span>
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
