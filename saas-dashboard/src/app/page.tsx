'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Bot, Zap, ChevronRight, ShieldCheck, Cpu, RefreshCw, Mail, MessageSquare, Terminal, CheckCircle2, ArrowUpRight, Globe, FileText } from "lucide-react";

export default function Home() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    let angle = 0;
    const render = () => {
      ctx.fillStyle = '#030305';
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.025)';
      ctx.lineWidth = 1;
      const step = 90;
      for (let x = 0; x < width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      ctx.save();
      ctx.translate(width * 0.85, height * 0.25);
      ctx.rotate(angle);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      ctx.lineWidth = 1.2;

      ctx.beginPath();
      ctx.arc(0, 0, 160, 0, Math.PI * 2);
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, 100, 0, Math.PI * 2);
      ctx.stroke();

      ctx.restore();
      angle += 0.003;

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  const SLACK_CLIENT_ID = process.env.NEXT_PUBLIC_SLACK_CLIENT_ID;
  const REDIRECT_URI = `${process.env.NEXT_PUBLIC_APP_URL}/api/auth/slack/callback`;
  const SLACK_OAUTH_URL = `https://slack.com/oauth/v2/authorize?client_id=${SLACK_CLIENT_ID}&scope=app_mentions:read,chat:write&redirect_uri=${REDIRECT_URI}`;

  const pipelineSteps = [
    {
      title: "01 // REAL-TIME WEBHOOK ENGINE",
      subtitle: "Instant Google Drive Event Synchronization",
      description: "Upon any document modification in Google Drive, secure background webhooks instantly dispatch payloads to the FastAPI backend. Built-in debouncing cooldowns optimize API usage and prevent rate-limit throttling.",
      badge: "STATUS: LISTENING // ACTIVE",
      icon: RefreshCw
    },
    {
      title: "02 // VECTOR NAMESPACE ISOLATION",
      subtitle: "Secure Pinecone Cloud Partitioning",
      description: "Parsed document chunks are converted via high-performance embeddings and safely persisted inside isolated Pinecone cloud indices segregated by strict workspace identifiers.",
      badge: "ENCRYPTED // SECURED",
      icon: Cpu
    },
    {
      title: "03 // SUB-SECOND SLACK RESOLUTION",
      subtitle: "Autonomous Channel Intelligence",
      description: "User queries dispatched via channel mentions trigger targeted vector similarity lookups, delivering precise, context-aware AI answers in milliseconds.",
      badge: "REAL-TIME DELIVERY",
      icon: ShieldCheck
    }
  ];

  return (
    <div className="min-h-screen bg-[#030305] text-white selection:bg-white selection:text-black font-sans relative overflow-x-hidden">
      
      <style jsx global>{`
        @keyframes smoothMarquee {
          0% { transform: translateX(0%); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee-custom {
          display: flex;
          width: max-content;
          animation: smoothMarquee 25s linear infinite;
        }
        .animate-marquee-custom:hover {
          animation-play-state: paused;
        }
      `}</style>

      <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none z-0" />

      {/* Navbar */}
      <nav className="flex justify-between items-center px-8 lg:px-16 py-6 max-w-7xl mx-auto relative z-20 border-b border-white/10 backdrop-blur-md sticky top-0 bg-[#030305]/90">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-white text-black font-black tracking-tighter">
            <Bot className="w-5 h-5" />
          </div>
          <div className="flex flex-col">
            <span className="font-mono font-bold text-base tracking-widest text-white uppercase">DocuBot <span className="text-gray-500">[ENTERPRISE]</span></span>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-8 font-mono text-xs tracking-widest text-gray-400">
          <a href="#pipeline" className="hover:text-white transition-colors">[01. WORKFLOW]</a>
          <a href="#docs-guide" className="hover:text-white transition-colors">[02. DOCS SYNC]</a>
          <a href="#pricing" className="hover:text-white transition-colors">[03. PRICING]</a>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-gray-300">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>NODE_ACTIVE</span>
          </div>
          <a 
            href={SLACK_OAUTH_URL}
            className="text-xs font-mono uppercase tracking-wider bg-white text-black px-5 py-2.5 rounded-none font-bold hover:bg-gray-200 transition-all flex items-center gap-2"
          >
            <span>Deploy</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </a>
        </div>
      </nav>

      {/* Ribbon Ticker */}
      <div className="w-full bg-[#0a0a0f] border-y border-white/10 py-3 overflow-hidden relative z-10 font-mono text-xs tracking-widest uppercase">
        <div className="animate-marquee-custom gap-8 items-center">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3 px-5 py-2 bg-white/5 border border-white/10 text-white font-bold skew-x-[-12deg]">
              <span className="w-2 h-2 rounded-full bg-pink-500"></span>
              <span>Slack Workspace OAuth</span>
            </div>
            <div className="flex items-center gap-3 px-5 py-2 bg-white/5 border border-white/10 text-emerald-400 font-bold skew-x-[-12deg]">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>Google Drive Webhooks</span>
            </div>
            <div className="flex items-center gap-3 px-5 py-2 bg-white/5 border border-white/10 text-purple-400 font-bold skew-x-[-12deg]">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
              <span>Pinecone Vector Namespaces</span>
            </div>
            <div className="flex items-center gap-3 px-5 py-2 bg-white/5 border border-white/10 text-blue-400 font-bold skew-x-[-12deg]">
              <span className="w-2 h-2 rounded-full bg-blue-400"></span>
              <span>FastAPI Async Workers</span>
            </div>
          </div>
          <div className="flex items-center gap-8 ml-8">
            <div className="flex items-center gap-3 px-5 py-2 bg-white/5 border border-white/10 text-white font-bold skew-x-[-12deg]">
              <span className="w-2 h-2 rounded-full bg-pink-500"></span>
              <span>Slack Workspace OAuth</span>
            </div>
            <div className="flex items-center gap-3 px-5 py-2 bg-white/5 border border-white/10 text-emerald-400 font-bold skew-x-[-12deg]">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>Google Drive Webhooks</span>
            </div>
            <div className="flex items-center gap-3 px-5 py-2 bg-white/5 border border-white/10 text-purple-400 font-bold skew-x-[-12deg]">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
              <span>Pinecone Vector Namespaces</span>
            </div>
            <div className="flex items-center gap-3 px-5 py-2 bg-white/5 border border-white/10 text-blue-400 font-bold skew-x-[-12deg]">
              <span className="w-2 h-2 rounded-full bg-blue-400"></span>
              <span>FastAPI Async Workers</span>
            </div>
          </div>
        </div>
      </div>

      {/* Hero Section */}
      <main className="flex flex-col items-start px-6 lg:px-20 pt-24 pb-20 relative z-10 max-w-7xl mx-auto">
        
        <div className="w-full flex justify-between items-center border-b border-white/10 pb-4 mb-12 font-mono text-xs text-gray-400">
          <div className="flex items-center gap-6">
            <span>FROM [GURUGRAM] <br /><span className="text-[10px] text-gray-600">28.4595° N, 77.0266° E</span></span>
            <span className="text-white/20">/ / /</span>
            <span>TO [CLOUD_EDGE] <br /><span className="text-[10px] text-gray-600">GLOBAL MULTI-TENANT REPO</span></span>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-emerald-400">
            <Globe className="w-4 h-4 animate-spin" />
            <span>GLOBAL SYNC READY</span>
          </div>
        </div>

        <div className="font-mono text-xs text-gray-400 tracking-widest uppercase mb-6 flex items-center gap-2 border-l-2 border-white pl-3">
          <span>MANIFESTO // AUTONOMOUS KNOWLEDGE ENGINE</span>
        </div>
        
        <h1 className="text-5xl sm:text-7xl md:text-9xl font-black tracking-tighter uppercase leading-[0.92] mb-8">
          Intelligence <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-400 to-gray-600">
            Requires Structure.
          </span>
        </h1>
        
        <p className="text-base sm:text-xl text-gray-400 max-w-3xl mb-12 font-mono leading-relaxed">
          We transform the chaotic ocean of enterprise Google Documents into governed, scalable vector fuel that powers instant decision-grade AI inside Slack.
        </p>
        
        {/* Main CTA */}
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-28">
          <a 
            href={SLACK_OAUTH_URL} 
            className="group relative inline-flex items-center justify-center gap-4 bg-white text-black px-10 py-5 text-sm font-mono uppercase tracking-widest font-extrabold hover:bg-gray-200 transition-all shadow-2xl"
          >
            <span>Add to Slack Workspace</span>
            <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </a>
        </div>

        {/* Pipeline Section */}
        <div id="pipeline" className="w-full mt-12 border-t border-white/20 pt-16">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-12 gap-4">
            <div>
              <span className="font-mono text-xs text-gray-400 uppercase tracking-widest">[01 // ARCHITECTURAL PIPELINE]</span>
              <h2 className="text-4xl md:text-6xl font-black tracking-tight uppercase mt-2">The Neural Core.</h2>
            </div>
            <p className="font-mono text-xs text-gray-400 max-w-xs">
              Inspect step-by-step data streams and event loops powering real-time synchronization.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
            {pipelineSteps.map((step, idx) => {
              const isActive = activeStep === idx;
              return (
                <button
                  key={idx}
                  onClick={() => setActiveStep(idx)}
                  className={`p-6 text-left transition-all font-mono border ${
                    isActive 
                      ? 'bg-white text-black border-white font-bold' 
                      : 'bg-black/80 text-gray-400 border-white/10 hover:border-white/30'
                  }`}
                >
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-xs">STAGE 0{idx + 1}</span>
                    {isActive ? <CheckCircle2 className="w-4 h-4 text-black" /> : <div className="w-2 h-2 rounded-full bg-gray-700" />}
                  </div>
                  <div className="text-sm tracking-wider uppercase">{step.title.split('//')[1]}</div>
                </button>
              );
            })}
          </div>

          <div className="p-10 bg-[#07070a] border border-white/20 relative overflow-hidden shadow-2xl">
            <div className="absolute top-0 right-0 p-8 font-mono text-8xl font-black text-white/5 pointer-events-none">
              0{activeStep + 1}
            </div>
            
            <div className="max-w-3xl relative z-10">
              <span className="inline-block px-3 py-1 bg-white/10 text-white font-mono text-xs mb-6 uppercase tracking-widest border border-white/20">
                {pipelineSteps[activeStep].badge}
              </span>
              <h3 className="text-2xl md:text-4xl font-black uppercase tracking-tight mb-4 text-white">
                {pipelineSteps[activeStep].subtitle}
              </h3>
              <p className="text-base text-gray-300 font-mono leading-relaxed">
                {pipelineSteps[activeStep].description}
              </p>
            </div>
          </div>
        </div>

        {/* Google Docs Integration & Onboarding Guide */}
        <div id="docs-guide" className="w-full mt-32 border-t border-white/20 pt-16">
          <div className="mb-12">
            <span className="font-mono text-xs text-gray-400 uppercase tracking-widest">[02 // GOOGLE DOCS SYNC GUIDE]</span>
            <h2 className="text-4xl md:text-6xl font-black tracking-tight uppercase mt-2">How Docs & Drive Connect.</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono">
            <div className="p-8 bg-[#07070a] border border-white/10 flex flex-col justify-between">
              <div>
                <span className="text-xs text-blue-400 block mb-2">STEP 1</span>
                <h3 className="text-xl font-bold uppercase text-white mb-3">Install Bot</h3>
                <p className="text-xs text-gray-400 leading-relaxed font-sans">
                  Click &quot;Add to Slack Workspace&quot; to authorize the multi-tenant OAuth connection securely[cite: 3].
                </p>
              </div>
              <div className="mt-8 pt-4 border-t border-white/10 text-[10px] text-gray-500 uppercase">INSTANT WORKSPACE SETUP</div>
            </div>

            <div className="p-8 bg-[#07070a] border border-white/10 flex flex-col justify-between">
              <div>
                <span className="text-xs text-emerald-400 block mb-2">STEP 2</span>
                <h3 className="text-xl font-bold uppercase text-white mb-3">Select Google Docs</h3>
                <p className="text-xs text-gray-400 leading-relaxed font-sans">
                  Link specific company folders or knowledge base documents via your secure tenant dashboard.
                </p>
              </div>
              <div className="mt-8 pt-4 border-t border-white/10 text-[10px] text-gray-500 uppercase">DRIVE API INTEGRATION</div>
            </div>

            <div className="p-8 bg-[#07070a] border border-white/10 flex flex-col justify-between">
              <div>
                <span className="text-xs text-purple-400 block mb-2">STEP 3</span>
                <h3 className="text-xl font-bold uppercase text-white mb-3">Auto-Sync & Ask</h3>
                <p className="text-xs text-gray-400 leading-relaxed font-sans">
                  Background webhooks keep vectors updated. Ask anything inside Slack using `@DocuBot`.
                </p>
              </div>
              <div className="mt-8 pt-4 border-t border-white/10 text-[10px] text-gray-500 uppercase">SUB-SECOND ANSWERS</div>
            </div>
          </div>
        </div>

        {/* Pricing & Plans Section */}
        <div id="pricing" className="w-full mt-32 border-t border-white/20 pt-16">
          <div className="mb-12">
            <span className="font-mono text-xs text-gray-400 uppercase tracking-widest">[03 // TRANSPARENT PRICING]</span>
            <h2 className="text-4xl md:text-6xl font-black tracking-tight uppercase mt-2">Choose Your Scale.</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 font-mono">
            
            {/* Free / Trial Plan */}
            <div className="p-10 bg-[#07070a] border border-white/10 flex flex-col justify-between relative">
              <div>
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs uppercase px-3 py-1 bg-white/5 border border-white/10 text-gray-300">Starter Trial</span>
                  <span className="text-2xl font-black">Free</span>
                </div>
                <h3 className="text-3xl font-black uppercase text-white mb-4">14-Day Full Access</h3>
                <p className="text-xs text-gray-400 font-sans leading-relaxed mb-8">
                  Perfect for testing autonomous vector knowledge retrieval inside your pilot Slack channel[cite: 3].
                </p>
                <ul className="space-y-3 text-xs text-gray-300 mb-8">
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Up to 50 Google Docs sync</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Standard AI query resolution</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Single Slack channel support</li>
                </ul>
              </div>
              <a 
                href={SLACK_OAUTH_URL}
                className="w-full py-4 bg-white/10 hover:bg-white/20 text-white text-center font-bold uppercase tracking-widest text-xs transition-all border border-white/20 block"
              >
                Start Free Trial
              </a>
            </div>

            {/* Enterprise Pro Plan */}
            <div className="p-10 bg-gradient-to-br from-blue-950/30 via-[#07070a] to-purple-950/30 border border-blue-500/50 flex flex-col justify-between relative shadow-2xl">
              <div className="absolute -top-3 right-8 px-3 py-1 bg-blue-600 text-white font-bold text-[10px] uppercase tracking-widest">
                Most Popular
              </div>
              <div>
                <div className="flex justify-between items-center mb-4">
                  <span className="text-xs uppercase px-3 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30">Enterprise Pro</span>
                  <span className="text-2xl font-black">$99<span className="text-xs font-normal text-gray-400"> /mo</span></span>
                </div>
                <h3 className="text-3xl font-black uppercase text-white mb-4">Unlimited Scale</h3>
                <p className="text-xs text-gray-400 font-sans leading-relaxed mb-8">
                  Designed for growing organizations requiring absolute data privacy and multi-channel synchronization.
                </p>
                <ul className="space-y-3 text-xs text-gray-300 mb-8">
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-blue-400" /> Unlimited Google Docs & Webhooks</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-blue-400" /> Isolated Pinecone vector namespaces</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-blue-400" /> Priority Gemini Vision AI model access</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-blue-400" /> Dedicated 24/7 enterprise support</li>
                </ul>
              </div>
              <a 
                href={SLACK_OAUTH_URL}
                className="w-full py-4 bg-white text-black hover:bg-gray-200 text-center font-bold uppercase tracking-widest text-xs transition-all block shadow-lg"
              >
                Deploy Enterprise Bot
              </a>
            </div>

          </div>
        </div>

      </main>

      {/* Footer */}
      <footer id="contact" className="border-t border-white/20 bg-[#020204] pt-20 pb-12 px-8 lg:px-16 font-mono text-xs relative z-20">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
          
          <div>
            <div className="font-bold text-sm tracking-widest text-white uppercase mb-4">[DOCUBOT.AI]</div>
            <p className="text-gray-400 leading-relaxed font-sans">
              Engineering enterprise-grade vector knowledge infrastructure for automated Slack resolutions.
            </p>
          </div>

          <div>
            <div className="text-white uppercase tracking-widest font-bold mb-4">Navigation</div>
            <ul className="space-y-2 text-gray-400">
              <li><a href="#pipeline" className="hover:text-white transition-colors">Core Pipeline</a></li>
              <li><a href="#docs-guide" className="hover:text-white transition-colors">Docs Sync Guide</a></li>
              <li><a href="#pricing" className="hover:text-white transition-colors">Pricing Tiers</a></li>
            </ul>
          </div>

          <div>
            <div className="text-white uppercase tracking-widest font-bold mb-4">Support & Feedback</div>
            <ul className="space-y-2 text-gray-400">
              <li className="flex items-center gap-2"><Mail className="w-3.5 h-3.5 text-white" /> <span>support@docubot.ai</span></li>
              <li className="flex items-center gap-2"><MessageSquare className="w-3.5 h-3.5 text-white" /> <span>Community Hub</span></li>
              <li><a href="#" className="hover:text-white transition-colors">System Status: Nominal</a></li>
            </ul>
          </div>

          <div>
            <div className="text-white uppercase tracking-widest font-bold mb-4">Headquarters</div>
            <p className="text-gray-400 leading-relaxed mb-4 font-sans">
              Gurugram Tech Hub<br />
              Haryana, India 122001
            </p>
            <div className="flex items-center gap-2 text-emerald-400">
              <Terminal className="w-3.5 h-3.5" />
              <span>PROD_ENV_READY</span>
            </div>
          </div>

        </div>

        <div className="max-w-7xl mx-auto border-t border-white/10 pt-8 flex flex-col sm:flex-row justify-between text-gray-500">
          <p>© 2026 DocuBot.ai Systems. All rights reserved.</p>
          <div className="flex gap-6 mt-4 sm:mt-0">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">Security</a>
          </div>
        </div>
      </footer>

    </div>
  );
}