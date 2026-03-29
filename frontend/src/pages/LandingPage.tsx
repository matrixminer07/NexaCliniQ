import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import CountUp from 'react-countup'
import { motion } from 'framer-motion'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import Particles, { initParticlesEngine } from '@tsparticles/react'
import { loadSlim } from '@tsparticles/slim'
import { Link } from 'react-router-dom'
import { api } from '@/services/api'

type StrategyOption = {
  id: string
  name: string
  summary: string
  timeline: string
  focus: string
}

type AnalysisResponse = {
  betterOption: string
  rationale: string
  riskNote: string
}

type StrategyFilter = 'all' | 'ai-first' | 'hybrid' | 'traditional'

const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0 },
}

const services = [
  {
    title: 'AI-Driven Drug Discovery',
    icon: 'AI',
    description:
      'Use translational models, molecular intelligence, and adaptive trial simulation to reduce late-phase attrition.',
  },
  {
    title: 'Traditional R&D Scaling',
    icon: 'RD',
    description:
      'Modernize legacy pipelines with deterministic decision frameworks and stage-gate optimization.',
  },
  {
    title: 'Biotech Partnerships',
    icon: 'BP',
    description:
      'Design partnership structures balancing platform leverage, licensing economics, and portfolio resilience.',
  },
]

const steps = [
  {
    title: 'Data Collection',
    description: 'Integrate molecular, clinical, and market datasets into one governed evidence layer.',
  },
  {
    title: 'Analysis',
    description: 'Run portfolio, financial, and risk engines to identify strategic asymmetries.',
  },
  {
    title: 'Strategy',
    description: 'Generate scenario-specific operating models and regulatory-aware investment paths.',
  },
  {
    title: 'Recommendation',
    description: 'Deliver board-ready decisions with transparent assumptions and execution guardrails.',
  },
]

const team = [
  {
    name: 'SPANDAN ROY',
    role: '',
    avatar: '/images/spandan.jpg',
    linkedin: 'https://www.linkedin.com/in/spandan-roy-39a634339/',
  },
  { name: 'AYAN ROY', role: '', avatar: '/images/team-2.svg', linkedin: 'https://www.linkedin.com/in/ayan-roy-73480b3ba/' },
  {
    name: 'FAGUN MANNA',
    role: '',
    avatar: '/images/team-3.svg',
    linkedin: 'https://www.linkedin.com/in/fagun-manna-387681371/',
  },
]

const testimonials = [
  {
    quote:
      'NexaClinIQ gave us a board-level strategy map in under two weeks and uncovered a partnership thesis we had overlooked.',
    name: 'COO, MidCap Biotech',
  },
  {
    quote:
      'The AI-versus-traditional model comparison changed our capital allocation and compressed trial planning cycles.',
    name: 'Head of Portfolio, Global Pharma',
  },
  {
    quote: 'Their regulatory timeline modeling was exceptionally practical and integrated seamlessly with our PMO cadence.',
    name: 'SVP, Clinical Operations',
  },
]

const trendData = [
  { month: 'Q1', feasibility: 62, readiness: 55 },
  { month: 'Q2', feasibility: 69, readiness: 61 },
  { month: 'Q3', feasibility: 75, readiness: 73 },
  { month: 'Q4', feasibility: 85, readiness: 85 },
]

const faqItems = [
  {
    question: 'How does the strategy recommendation process work?',
    answer:
      'We combine molecular, operational, financial, and regulatory inputs to score options against your portfolio goals.',
  },
  {
    question: 'What are key AI risks in biotech planning?',
    answer:
      'Model drift, data quality constraints, and explainability gaps. We address these with transparent assumptions and staged controls.',
  },
  {
    question: 'How quickly can teams see actionable outcomes?',
    answer: 'Most organizations receive a first strategic decision pack within 10-15 business days.',
  },
  {
    question: 'Can NexaClinIQ support portfolio prioritization across multiple assets?',
    answer:
      'Yes. We rank assets using probability of technical success, market attractiveness, capital intensity, and timeline risk to support portfolio sequencing.',
  },
  {
    question: 'How is model transparency handled for executive and audit reviews?',
    answer:
      'Every recommendation includes traceable assumptions, scenario sensitivities, and explainability outputs so teams can defend decisions with confidence.',
  },
  {
    question: 'Does the platform fit early-stage biotech teams with limited resources?',
    answer:
      'Yes. Teams can start with focused strategy cycles and expand to broader portfolio and market modules as programs mature.',
  },
  {
    question: 'Can your framework align with regulatory planning milestones?',
    answer:
      'Yes. We model milestone pathways around IND-enabling, Phase transitions, and evidence requirements to keep strategy aligned with regulatory timing.',
  },
  {
    question: 'What data does NexaClinIQ need to get started?',
    answer:
      'A baseline can begin with target program summaries, stage status, assumptions, and budget constraints. We then enrich with internal and external datasets.',
  },
]

const strategyHighlights = [
  'Probability-adjusted asset ranking',
  'Regulatory timing and evidence mapping',
  'Capital efficiency and downside controls',
]

const strategyFilters: { id: StrategyFilter; label: string }[] = [
  { id: 'all', label: 'All strategies' },
  { id: 'ai-first', label: 'AI-first' },
  { id: 'hybrid', label: 'Hybrid' },
  { id: 'traditional', label: 'Traditional' },
]

const strategyTypeLabel: Record<Exclude<StrategyFilter, 'all'>, string> = {
  'ai-first': 'AI-first',
  hybrid: 'Hybrid',
  traditional: 'Traditional',
}

function inferStrategyType(option: StrategyOption): Exclude<StrategyFilter, 'all'> {
  const text = `${option.name} ${option.focus} ${option.summary}`.toLowerCase()

  if (text.includes('hybrid')) return 'hybrid'
  if (text.includes('traditional') || text.includes('legacy')) return 'traditional'
  return 'ai-first'
}

function getStrategyConfidence(option: StrategyOption): number {
  const seed = `${option.id}-${option.name}-${option.timeline}`
  let hash = 0

  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash << 5) - hash + seed.charCodeAt(i)
    hash |= 0
  }

  return 78 + (Math.abs(hash) % 21)
}

function getConfidenceTrend(option: StrategyOption): { arrow: string; label: string; tone: string } {
  const text = `${option.timeline} ${option.summary} ${option.focus}`.toLowerCase()

  if (text.includes('fast') || text.includes('accelerat') || text.includes('ready') || text.includes('near-term')) {
    return { arrow: '↑', label: 'Rising', tone: 'text-emerald-300 border-emerald-400/40 bg-emerald-500/15' }
  }

  if (text.includes('risk') || text.includes('delay') || text.includes('uncertain') || text.includes('long-term')) {
    return { arrow: '↓', label: 'Watch', tone: 'text-amber-300 border-amber-400/40 bg-amber-500/15' }
  }

  return { arrow: '→', label: 'Stable', tone: 'text-sky-200 border-sky-300/35 bg-sky-500/10' }
}

function ProgressRing({ label, value }: { label: string; value: number }) {
  const radius = 45
  const circumference = 2 * Math.PI * radius
  const dash = (value / 100) * circumference

  return (
    <div className="flex items-center gap-4">
      <svg width="110" height="110" className="-rotate-90">
        <circle cx="55" cy="55" r={radius} stroke="rgba(255,255,255,0.14)" strokeWidth="10" fill="none" />
        <circle
          cx="55"
          cy="55"
          r={radius}
          stroke="#00c2ff"
          strokeWidth="10"
          fill="none"
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
        />
      </svg>
      <div>
        <div className="text-3xl font-bold text-white">{value}%</div>
        <div className="text-sm text-[#8ba8c4]">{label}</div>
      </div>
    </div>
  )
}

export function LandingPage() {
  const [showNavbarBorder, setShowNavbarBorder] = useState(false)
  const [kpiVisible, setKpiVisible] = useState(false)
  const [strategies, setStrategies] = useState<StrategyOption[]>([])
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [contactStatus, setContactStatus] = useState<string>('')
  const [particlesReady, setParticlesReady] = useState(false)
  const [showAllFaqs, setShowAllFaqs] = useState(false)
  const [strategiesLoading, setStrategiesLoading] = useState(true)
  const [analysisLoading, setAnalysisLoading] = useState(true)
  const [strategyFilter, setStrategyFilter] = useState<StrategyFilter>('all')
  const kpiRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const onScroll = () => setShowNavbarBorder(window.scrollY > 14)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    let mounted = true
    initParticlesEngine(async (engine) => {
      await loadSlim(engine)
    }).then(() => {
      if (mounted) setParticlesReady(true)
    })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setKpiVisible(true)
          observer.disconnect()
        }
      },
      { threshold: 0.3 }
    )

    if (kpiRef.current) observer.observe(kpiRef.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    setStrategiesLoading(true)
    setAnalysisLoading(true)

    api
      .nexusStrategies()
      .then((res) => setStrategies(res.options))
      .catch(() => setStrategies([]))
      .finally(() => setStrategiesLoading(false))

    api
      .nexusAnalysis({ mode: 'ai-vs-traditional' })
      .then((res) => setAnalysis(res))
      .catch(() => setAnalysis(null))
      .finally(() => setAnalysisLoading(false))
  }, [])

  const particleOptions = useMemo(
    () => ({
      background: { color: { value: 'transparent' } },
      fpsLimit: 60,
      particles: {
        color: { value: '#00c2ff' },
        links: { color: '#1a6bb5', distance: 110, enable: true, opacity: 0.18, width: 1 },
        move: { enable: true, speed: 0.9, outModes: { default: 'out' as const } },
        number: { value: 40, density: { enable: true } },
        opacity: { value: 0.25 },
        size: { value: { min: 1, max: 3 } },
      },
      detectRetina: true,
    }),
    []
  )

  const visibleFaqItems = useMemo(
    () => (showAllFaqs ? faqItems : faqItems.slice(0, 4)),
    [showAllFaqs]
  )

  const filteredStrategies = useMemo(() => {
    const source =
      strategyFilter === 'all'
        ? strategies
        : strategies.filter((option) => inferStrategyType(option) === strategyFilter)

    return [...source].sort((a, b) => getStrategyConfidence(b) - getStrategyConfidence(a))
  }, [strategies, strategyFilter])

  async function onContactSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const email = String(form.get('email') || '')
    const payload = {
      name: 'Newsletter Subscriber',
      email,
      company: 'NexaClinIQ Newsletter',
      message: 'Please add me to NexaClinIQ updates.',
    }

    try {
      const res = await api.nexusContact(payload)
      setContactStatus(res.message || 'Message received.')
      event.currentTarget.reset()
    } catch {
      setContactStatus('Unable to submit right now. Please try again.')
    }
  }

  return (
    <div className="pharma-landing bg-[#0a0f1e] text-white font-body">
      <header
        className={`fixed top-0 z-50 w-full backdrop-blur-md bg-[rgba(10,15,30,0.72)] transition-all ${
          showNavbarBorder ? 'border-b border-[rgba(255,255,255,0.1)]' : 'border-b border-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-6">
          <div className="flex items-center gap-4 shrink-0">
            <a href="#hero" className="inline-flex items-center" aria-label="NexaClinIQ Home">
              <img
                src="/logo.png"
                alt="NexaClinIQ"
                className="h-12 w-auto object-contain"
              />
            </a>
          </div>
          <div className="ml-auto flex items-center gap-6">
            <nav className="hidden md:flex items-center gap-8 text-sm text-[#8ba8c4] whitespace-nowrap">
              <a href="#services" className="hover:text-white transition-colors">Services</a>
              <a href="#about" className="hover:text-white transition-colors">About</a>
              <a href="#process" className="hover:text-white transition-colors">Process</a>
              <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
            </nav>
            <Link to="/login" className="rounded-full bg-[#1a6bb5] px-5 py-2.5 text-sm font-semibold hover:bg-[#00c2ff] hover:text-[#0a0f1e] transition-all">
              Login
            </Link>
          </div>
        </div>
      </header>

      <section id="hero" className="relative min-h-screen flex items-center justify-center overflow-hidden px-6">
        <video
          className="absolute inset-0 h-full w-full object-cover object-center"
          autoPlay
          loop
          muted
          playsInline
          preload="metadata"
          aria-hidden="true"
          disablePictureInPicture
        >
          <source src="/videos/intro-hero-landscape-v2.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_16%,rgba(0,194,255,0.14),transparent_38%),radial-gradient(circle_at_88%_20%,rgba(26,107,181,0.20),transparent_42%),linear-gradient(145deg,rgba(10,15,30,0.78)_0%,rgba(11,30,61,0.84)_100%)]" />
        {particlesReady && <Particles id="pn-particles" className="absolute inset-0" options={particleOptions} />}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="relative z-10 text-center max-w-4xl"
        >
          <p className="uppercase tracking-[0.28em] text-xs text-[#8ba8c4] mb-6">NexaClinIQ Strategy Intelligence</p>
          <h1 className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.24] md:leading-[1.16] max-w-4xl mx-auto">
            <span className="block">AI is Redefining</span>
            <span className="block">Drug Discovery</span>
          </h1>
          <p className="mt-6 text-xl text-[#8ba8c4]">Smarter R&D. Faster Trials. Better Outcomes.</p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <a href="#services" className="rounded-full bg-[#1a6bb5] px-7 py-3 font-semibold hover:bg-[#00c2ff] hover:text-[#0a0f1e] transition-colors">
              Explore Strategy
            </a>
          </div>
        </motion.div>
        <a href="#stats" className="absolute bottom-8 left-1/2 -translate-x-1/2 text-[#8ba8c4] animate-bounce" aria-label="Scroll to stats">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M6 9L12 15L18 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>
      </section>

      <motion.section
        id="stats"
        ref={kpiRef}
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.35 }}
        transition={{ duration: 0.55 }}
        className="bg-[#07152d] border-y border-[rgba(255,255,255,0.06)]"
      >
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { end: 430, suffix: '+', label: 'Staff' },
            { end: 3, suffix: '', label: 'Strategic Options' },
            { end: 500, suffix: 'M', prefix: '$', label: 'Funding' },
            { end: 5, suffix: '', label: 'Year Roadmap' },
          ].map((item) => (
            <div key={item.label}>
              <div className="text-3xl font-display font-bold text-[#00c2ff]">
                {kpiVisible ? (
                  <CountUp end={item.end} duration={2.1} prefix={item.prefix ?? ''} suffix={item.suffix} />
                ) : (
                  `${item.prefix ?? ''}0${item.suffix}`
                )}
              </div>
              <p className="mt-2 text-[#8ba8c4] text-sm">{item.label}</p>
            </div>
          ))}
        </div>
      </motion.section>

      <motion.section
        id="services"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.55 }}
        className="max-w-6xl mx-auto px-6 py-24"
      >
        <h2 className="font-display text-4xl md:text-5xl">Our Strategic Analysis Areas</h2>
        <div className="mt-10 grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))]">
          {services.map((service) => (
            <article
              key={service.title}
              className="pn-glass rounded-2xl p-7 transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_0_22px_rgba(0,194,255,0.34)]"
            >
              <div className="h-12 w-12 rounded-full border border-[rgba(0,194,255,0.45)] bg-[rgba(26,107,181,0.2)] flex items-center justify-center font-display">
                {service.icon}
              </div>
              <h3 className="mt-5 text-2xl font-display">{service.title}</h3>
              <p className="mt-3 text-[#8ba8c4] leading-relaxed">{service.description}</p>
              <a href="#pricing" className="inline-block mt-5 text-[#00c2ff] hover:underline">Learn More</a>
            </article>
          ))}
        </div>
      </motion.section>

      <section className="overflow-hidden border-y border-[rgba(255,255,255,0.08)] bg-[#0b1e3d] py-4">
        <div className="pn-marquee text-sm md:text-base text-[#8ba8c4] whitespace-nowrap">
          <span>
            Computational Biology + AI Platforms + Clinical Trials + Regulatory Strategy + Market Analysis +
          </span>
          <span>
            Computational Biology + AI Platforms + Clinical Trials + Regulatory Strategy + Market Analysis +
          </span>
        </div>
      </section>

      <motion.section
        id="about"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.55 }}
        className="max-w-6xl mx-auto px-6 py-24 grid lg:grid-cols-2 gap-10 items-center"
      >
        <img
          src="/images/lab-scientist.svg"
          alt="Lab scientist"
          className="w-full rounded-3xl border border-[rgba(255,255,255,0.1)] shadow-[0_24px_60px_rgba(0,0,0,0.45)]"
        />
        <div>
          <h2 className="font-display text-4xl md:text-5xl">Who We Are</h2>
          <p className="mt-5 text-[#8ba8c4] leading-relaxed">
            NexaClinIQ combines translational science, AI systems engineering, and biopharma operating expertise to
            help leadership teams make bolder decisions with clearer evidence.
          </p>
          <div className="mt-8 grid sm:grid-cols-2 gap-6">
            <ProgressRing label="Scientific Feasibility" value={85} />
            <ProgressRing label="Market Readiness" value={85} />
          </div>
          <div className="mt-8 pn-glass rounded-2xl p-5 h-48">
            <p className="text-sm text-[#8ba8c4] mb-3">Readiness Trajectory</p>
            {!trendData || trendData.length === 0 ? (
              <div className="h-[300px] flex items-center justify-center text-[#8ba8c4]">No data available</div>
            ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={trendData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="feasibility" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00c2ff" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#00c2ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: '#8ba8c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#8ba8c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#0b1e3d', border: '1px solid rgba(255,255,255,0.1)' }} />
                <Area type="monotone" dataKey="feasibility" stroke="#00c2ff" fill="url(#feasibility)" />
              </AreaChart>
            </ResponsiveContainer>
            )}
          </div>
        </div>
      </motion.section>

      <motion.section
        id="process"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.55 }}
        className="bg-[#0b1e3d] py-24"
      >
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="font-display text-4xl md:text-5xl">How It Works</h2>
          <div className="mt-12 pn-steps relative grid md:grid-cols-4 gap-6">
            {steps.map((step, index) => (
              <article key={step.title} className="pn-glass rounded-2xl p-6 relative">
                <div className="h-10 w-10 rounded-full border border-[rgba(0,194,255,0.7)] bg-[rgba(0,194,255,0.12)] flex items-center justify-center font-semibold">
                  {index + 1}
                </div>
                <h3 className="mt-4 font-display text-2xl">{step.title}</h3>
                <p className="mt-2 text-sm text-[#8ba8c4]">{step.description}</p>
              </article>
            ))}
          </div>
        </div>
      </motion.section>

      <motion.section
        id="pricing"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.55 }}
        className="max-w-6xl mx-auto px-6 py-24"
      >
        <h2 className="font-display text-4xl md:text-5xl">Strategy Tiers</h2>
        <div className="mt-10 grid md:grid-cols-3 gap-6 items-stretch">
          {[
            { name: 'Traditional Pharma', price: '$199', label: 'Basic' },
            { name: 'Hybrid Approach', price: '$299', label: 'Standard', featured: true },
            { name: 'AI-First', price: '$399', label: 'Premium' },
          ].map((tier) => (
            <article
              key={tier.name}
              className={`pn-glass rounded-2xl p-7 ${
                tier.featured
                  ? 'scale-[1.04] border border-[rgba(0,194,255,0.8)] shadow-[0_0_28px_rgba(0,194,255,0.35)]'
                  : ''
              }`}
            >
              <p className="text-sm uppercase tracking-[0.18em] text-[#8ba8c4]">{tier.label}</p>
              <h3 className="mt-3 text-2xl font-display">{tier.name}</h3>
              <p className="mt-5 text-5xl font-display">{tier.price}</p>
              <p className="mt-2 text-sm text-[#8ba8c4]">per strategic cycle</p>
              <button className="mt-8 w-full rounded-full bg-[#1a6bb5] py-3 font-semibold hover:bg-[#00c2ff] hover:text-[#0a0f1e] transition-colors">
                Choose Plan
              </button>
            </article>
          ))}
        </div>
      </motion.section>

      <motion.section
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.55 }}
        className="max-w-6xl mx-auto px-6 pb-24"
      >
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h2 className="font-display text-4xl md:text-5xl">Live Strategy Options</h2>
            <p className="mt-3 max-w-2xl text-[#8ba8c4] leading-relaxed">
              Explore portfolio paths generated from scientific feasibility, financial return pressure, and regulatory constraints.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {strategyFilters.map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  onClick={() => setStrategyFilter(filter.id)}
                  className={`rounded-full px-4 py-2 text-xs font-semibold transition-colors ${
                    strategyFilter === filter.id
                      ? 'bg-[#00c2ff] text-[#0a0f1e]'
                      : 'border border-[rgba(255,255,255,0.16)] bg-[rgba(255,255,255,0.04)] text-[#8ba8c4] hover:border-[rgba(0,194,255,0.45)] hover:text-[#9ddff6]'
                  }`}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {strategyHighlights.map((highlight) => (
              <span
                key={highlight}
                className="rounded-full border border-[rgba(0,194,255,0.35)] bg-[rgba(0,194,255,0.1)] px-3 py-1 text-xs text-[#9ddff6]"
              >
                {highlight}
              </span>
            ))}
          </div>
        </div>

        <div className="mt-8 grid md:grid-cols-3 gap-5">
          {strategiesLoading &&
            Array.from({ length: 3 }).map((_, index) => (
              <article key={`strategy-skeleton-${index}`} className="pn-glass rounded-2xl p-6 animate-pulse">
                <div className="h-6 w-2/3 rounded bg-[rgba(255,255,255,0.1)]" />
                <div className="mt-3 h-3 w-full rounded bg-[rgba(255,255,255,0.08)]" />
                <div className="mt-2 h-3 w-5/6 rounded bg-[rgba(255,255,255,0.08)]" />
                <div className="mt-6 h-3 w-1/2 rounded bg-[rgba(255,255,255,0.08)]" />
                <div className="mt-2 h-3 w-2/3 rounded bg-[rgba(255,255,255,0.08)]" />
              </article>
            ))}

          {!strategiesLoading &&
            filteredStrategies.map((option, index) => (
              <motion.article
                key={option.id}
                initial={{ opacity: 0, y: 22 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: 'easeOut', delay: index * 0.08 }}
                className="pn-glass rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_0_24px_rgba(0,194,255,0.28)]"
              >
                {(() => {
                  const trend = getConfidenceTrend(option)
                  return (
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-[#00c2ff]">{strategyTypeLabel[inferStrategyType(option)]}</p>
                  <div className="flex flex-col items-end gap-1">
                    <span className="rounded-full border border-[rgba(0,194,255,0.45)] bg-[rgba(0,194,255,0.13)] px-2.5 py-1 text-[11px] font-semibold text-[#9ddff6]">
                      Confidence {getStrategyConfidence(option)}%
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${trend.tone}`}>
                      {trend.arrow} {trend.label}
                    </span>
                  </div>
                </div>
                  )
                })()}
                <h3 className="mt-2 font-display text-2xl">{option.name}</h3>
                <p className="mt-3 text-sm text-[#8ba8c4] leading-relaxed">{option.summary}</p>
                <p className="mt-5 text-xs uppercase tracking-[0.2em] text-[#8ba8c4]">{option.timeline}</p>
                <p className="mt-1 text-sm text-[#8ba8c4]">{option.focus}</p>
              </motion.article>
            ))}
        </div>

        {!strategiesLoading && strategies.length > 0 && filteredStrategies.length === 0 && (
          <div className="mt-6 rounded-2xl border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.03)] p-6">
            <p className="text-sm uppercase tracking-[0.18em] text-[#8ba8c4]">No matches for this filter</p>
            <p className="mt-2 text-[#8ba8c4]">Try another strategy type to view available live options.</p>
          </div>
        )}

        {!strategiesLoading && strategies.length === 0 && (
          <div className="mt-6 rounded-2xl border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.03)] p-6">
            <p className="text-sm uppercase tracking-[0.18em] text-[#8ba8c4]">Strategy feed unavailable</p>
            <h3 className="mt-2 font-display text-2xl text-white">Curated strategy templates are still available</h3>
            <p className="mt-3 text-[#8ba8c4]">
              While live scenarios refresh, teams can continue with template-driven planning for trial design, capital allocation, and partner strategy.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {strategyHighlights.map((highlight) => (
                <span key={`fallback-${highlight}`} className="rounded-full bg-[rgba(255,255,255,0.06)] px-3 py-1 text-xs text-[#8ba8c4]">
                  {highlight}
                </span>
              ))}
            </div>
          </div>
        )}

        {analysisLoading && (
          <div className="mt-6 rounded-2xl border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.03)] p-6 animate-pulse">
            <div className="h-3 w-24 rounded bg-[rgba(255,255,255,0.08)]" />
            <div className="mt-3 h-7 w-1/3 rounded bg-[rgba(255,255,255,0.1)]" />
            <div className="mt-4 h-3 w-full rounded bg-[rgba(255,255,255,0.08)]" />
            <div className="mt-2 h-3 w-5/6 rounded bg-[rgba(255,255,255,0.08)]" />
          </div>
        )}

        {!analysisLoading && analysis && (
          <div className="mt-6 rounded-2xl border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.03)] p-6">
            <p className="text-sm text-[#8ba8c4]">AI Comparison</p>
            <h3 className="mt-2 font-display text-2xl text-[#00c2ff]">{analysis.betterOption}</h3>
            <p className="mt-3 text-[#8ba8c4] leading-relaxed">{analysis.rationale}</p>
            <p className="mt-2 text-sm text-[#8ba8c4]">{analysis.riskNote}</p>
          </div>
        )}
      </motion.section>

      <motion.section
        id="team"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.55 }}
        className="max-w-6xl mx-auto px-6 pb-24"
      >
        <h2 className="font-display text-4xl md:text-5xl">Team</h2>
        <p className="mt-3 max-w-2xl text-[#8ba8c4]">
          A focused blend of strategy, science, and execution driving measurable outcomes.
        </p>
        <div className="mt-10 grid [grid-template-columns:repeat(auto-fit,minmax(220px,1fr))] gap-6">
          {team.map((member) => (
            <article
              key={member.name}
              className="group relative overflow-hidden rounded-2xl border border-[rgba(0,194,255,0.25)] bg-[linear-gradient(145deg,rgba(15,30,56,0.92),rgba(10,20,40,0.88))] p-6 shadow-[0_14px_36px_rgba(2,11,24,0.35)] transition-all duration-300 hover:-translate-y-1 hover:border-[rgba(0,194,255,0.5)] hover:shadow-[0_18px_44px_rgba(0,194,255,0.2)]"
            >
              <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-[radial-gradient(circle,rgba(0,194,255,0.42),rgba(0,194,255,0)_65%)] blur-md transition-opacity duration-300 group-hover:opacity-100" />
              <div className="relative h-[60px] w-[60px] rounded-full border border-[rgba(255,255,255,0.24)] bg-[linear-gradient(135deg,#1e40af,#00c2ff)] text-white text-[18px] font-semibold flex items-center justify-center shadow-[0_10px_25px_rgba(37,99,235,0.35)]">
                {member.name
                  .split(' ')
                  .filter(Boolean)
                  .slice(0, 2)
                  .map((part) => part[0])
                  .join('')}
              </div>
              <h3 className="mt-4 text-[16px] font-semibold text-white">{member.name}</h3>
              {member.role ? (
                <p className="mt-1 inline-flex rounded-full border border-[rgba(0,194,255,0.35)] bg-[rgba(0,194,255,0.12)] px-3 py-1 text-[12px] font-medium text-[#8de6ff]">
                  {member.role}
                </p>
              ) : null}
              <p className="mt-4 text-[13px] leading-relaxed text-[#a9bfd8]">
                Building high-confidence strategy pathways from discovery to clinical translation.
              </p>
              <div className="mt-5 flex items-center gap-4 text-sm text-[#8ba8c4]">
                <a
                  href={member.linkedin}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-full border border-[rgba(139,168,196,0.35)] px-3 py-1.5 transition-colors hover:border-[rgba(0,194,255,0.6)] hover:text-[#00c2ff]"
                >
                  LinkedIn
                </a>
              </div>
            </article>
          ))}
        </div>
      </motion.section>

      <motion.section
        id="testimonials"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.55 }}
        className="max-w-6xl mx-auto px-6 pb-24"
      >
        <h2 className="font-display text-4xl md:text-5xl">Testimonials</h2>
        <div className="mt-10 flex gap-5 overflow-x-auto snap-x snap-mandatory pb-2">
          {testimonials.map((item) => (
            <article key={item.name} className="min-w-[320px] md:min-w-[420px] snap-start pn-glass rounded-2xl p-7">
              <p className="text-lg leading-relaxed">"{item.quote}"</p>
              <p className="mt-5 text-sm text-[#8ba8c4]">{item.name}</p>
            </article>
          ))}
        </div>
      </motion.section>

      <motion.section
        id="faq"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.55 }}
        className="max-w-4xl mx-auto px-6 pb-24"
      >
        <h2 className="font-display text-4xl md:text-5xl">FAQ</h2>
        <div className="mt-8 space-y-4">
          {visibleFaqItems.map((item) => (
            <details key={item.question} className="pn-glass rounded-2xl p-5 group">
              <summary className="cursor-pointer font-semibold">{item.question}</summary>
              <p className="mt-3 text-[#8ba8c4]">{item.answer}</p>
            </details>
          ))}
        </div>
        {faqItems.length > 4 && (
          <div className="mt-6 flex justify-center">
            <button
              type="button"
              onClick={() => setShowAllFaqs((prev) => !prev)}
              className="rounded-full bg-[#1a6bb5] px-6 py-2.5 text-sm font-semibold hover:bg-[#00c2ff] hover:text-[#0a0f1e] transition-colors"
            >
              {showAllFaqs ? 'View less' : 'View more'}
            </button>
          </div>
        )}
      </motion.section>

      <section id="newsletter" className="bg-[#07152d] border-y border-[rgba(255,255,255,0.08)] py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="font-display text-4xl">Stay Ahead in Biotech Strategy</h2>
          <p className="mt-3 text-[#8ba8c4]">Get curated intelligence on AI-driven drug development and market inflection points.</p>
          <form onSubmit={onContactSubmit} className="mt-8 flex flex-col sm:flex-row gap-3 max-w-xl mx-auto">
            <input name="email" type="email" placeholder="Email address" className="pn-input flex-1" required />
            <button type="submit" className="rounded-full bg-[#1a6bb5] py-3 px-8 font-semibold hover:bg-[#00c2ff] hover:text-[#0a0f1e] transition-colors">
              Subscribe
            </button>
          </form>
          {contactStatus && <p className="mt-4 text-sm text-[#00c2ff]">{contactStatus}</p>}
        </div>
      </section>

      <footer className="max-w-6xl mx-auto px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-[#8ba8c4]">
        <p className="font-display text-white">NexaClinIQ</p>
        <div className="flex items-center gap-5">
          <a href="#hero" className="hover:text-white">Home</a>
          <a href="#services" className="hover:text-white">Services</a>
          <a href="#about" className="hover:text-white">About</a>
          <a href="#faq" className="hover:text-white">FAQ</a>
        </div>
        <div className="flex items-center gap-3">
          <a href="#" className="hover:text-white">LinkedIn</a>
          <a href="#" className="hover:text-white">X</a>
        </div>
        <p>Copyright 2026 NexaClinIQ. All rights reserved.</p>
      </footer>
    </div>
  )
}
