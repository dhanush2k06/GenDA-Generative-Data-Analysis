import React from 'react';
import { 
  FolderSearch, 
  FileCheck2, 
  Eye, 
  Trash2, 
  ShieldAlert,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import { LifecycleStage } from '../types';

interface LifecycleTrackerProps {
  currentStage: LifecycleStage;
  fileCount: number;
  previewedCount: number;
}

interface StepInfo {
  id: LifecycleStage;
  label: string;
  sub: string;
  icon: React.ElementType;
}

const STEPS: StepInfo[] = [
  { id: 'select', label: '1. Select', sub: 'Files or Folder', icon: FolderSearch },
  { id: 'access', label: '2. Access Locally', sub: 'Native File APIs', icon: FileCheck2 },
  { id: 'preview', label: '3. Preview', sub: 'Temporary RAM parsing', icon: Eye },
  { id: 'clear', label: '4. Clear', sub: 'Wipe App State', icon: Trash2 },
  { id: 'released', label: '5. Release Access', sub: 'Zero Retention / GC', icon: ShieldAlert },
];

export const LifecycleTracker: React.FC<LifecycleTrackerProps> = ({ 
  currentStage, 
  fileCount, 
  previewedCount 
}) => {
  const getStepStatus = (stepId: LifecycleStage, index: number) => {
    const stageOrder: LifecycleStage[] = ['select', 'access', 'preview', 'clear', 'released'];
    const currentIndex = stageOrder.indexOf(currentStage);

    if (currentStage === 'released' || currentStage === 'clear') {
      if (stepId === currentStage) return 'active';
      return index < currentIndex ? 'completed' : 'pending';
    }

    if (index < currentIndex) return 'completed';
    if (index === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="w-full glass-panel rounded-2xl p-4 sm:p-5 mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-gray-800/80">
        <div>
          <h2 className="text-sm font-semibold tracking-wide uppercase text-emerald-400 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            Local Data Lifecycle Pipeline
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Full client-side progression with zero backend communication or storage
          </p>
        </div>

        <div className="text-xs text-gray-400 flex items-center gap-3">
          <span className="bg-gray-800/80 px-2.5 py-1 rounded-md text-gray-300 font-mono">
            Files in State: <strong className="text-emerald-400">{fileCount}</strong>
          </span>
          <span className="bg-gray-800/80 px-2.5 py-1 rounded-md text-gray-300 font-mono">
            Previewed: <strong className="text-cyan-400">{previewedCount}</strong>
          </span>
        </div>
      </div>

      {/* Steps Flow */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 sm:gap-4 relative">
        {STEPS.map((step, idx) => {
          const status = getStepStatus(step.id, idx);
          const Icon = step.icon;

          return (
            <div 
              key={step.id}
              className={`relative flex flex-col p-3 rounded-xl border transition-all duration-300 ${
                status === 'active'
                  ? 'bg-emerald-500/10 border-emerald-500/50 shadow-glow text-emerald-300'
                  : status === 'completed'
                  ? 'bg-gray-900/90 border-gray-700/80 text-gray-200'
                  : 'bg-gray-950/40 border-gray-800/50 text-gray-500 opacity-60'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className={`p-2 rounded-lg ${
                  status === 'active'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : status === 'completed'
                    ? 'bg-emerald-950/50 text-emerald-400'
                    : 'bg-gray-900 text-gray-600'
                }`}>
                  <Icon className="w-4 h-4" />
                </div>
                {status === 'completed' && (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                )}
                {status === 'active' && (
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 animate-pulse">
                    Current
                  </span>
                )}
              </div>

              <span className="font-semibold text-xs text-gray-100">{step.label}</span>
              <span className="text-[11px] text-gray-400 mt-0.5">{step.sub}</span>

              {/* Arrow on desktop */}
              {idx < STEPS.length - 1 && (
                <div className="hidden md:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10 text-gray-700">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
