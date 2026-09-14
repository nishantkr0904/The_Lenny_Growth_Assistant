import React from 'react';
import { EvidenceTier } from '../../types';
import { ShieldCheck, AlertTriangle, Layers } from 'lucide-react';

interface EvidenceIndicatorProps {
  tier?: EvidenceTier;
  sourcesCount?: number;
}

export const EvidenceIndicator: React.FC<EvidenceIndicatorProps> = ({ tier, sourcesCount = 0 }) => {
  if (!tier || tier === 'insufficient') {
    return null;
  }

  if (tier === 'strong') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <ShieldCheck className="w-3 h-3 mr-1 text-emerald-600" />
        Strong Evidence {sourcesCount > 0 ? `· ${sourcesCount} source${sourcesCount > 1 ? 's' : ''}` : ''}
      </span>
    );
  }

  if (tier === 'limited') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
        <AlertTriangle className="w-3 h-3 mr-1 text-amber-600" />
        Limited Evidence {sourcesCount > 0 ? `· ${sourcesCount} source${sourcesCount > 1 ? 's' : ''}` : ''}
      </span>
    );
  }

  if (tier === 'conflicting') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
        <Layers className="w-3 h-3 mr-1 text-blue-600" />
        Contrasting Perspectives {sourcesCount > 0 ? `· ${sourcesCount} sources` : ''}
      </span>
    );
  }

  return null;
};
