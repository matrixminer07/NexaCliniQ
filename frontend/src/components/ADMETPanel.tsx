import type { AdmetProfile } from '@/types'
import { GlossaryTooltip } from '@/components/GlossaryTooltip'

interface ADMETPanelProps {
  admet: AdmetProfile
}

export function ADMETPanel({ admet }: ADMETPanelProps) {
  return (
    <div className="card-p space-y-3">
      <h3 className="font-display text-lg">ADMET Profile</h3>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="text-ink-secondary">MW</div><div className="font-mono">{admet.mw_daltons.toFixed(1)} Da</div>
        <div className="text-ink-secondary">LogP</div><div className="font-mono">{admet.logp_estimate.toFixed(2)}</div>
        <div className="text-ink-secondary"><GlossaryTooltip term="lipinski">Lipinski</GlossaryTooltip></div><div>{admet.lipinski_pass ? 'Pass' : 'Needs work'}</div>
        <div className="text-ink-secondary"><GlossaryTooltip term="hERG">hERG</GlossaryTooltip></div><div>{admet.herg_risk ? 'Caution' : 'Safe profile'}</div>
        <div className="text-ink-secondary">Drug likeness</div><div>{admet.drug_likeness}</div>
      </div>
      {(admet.admet_warnings ?? []).length > 0 && (
        <div className="text-xs text-state-caution">Focus: {(admet.admet_warnings ?? []).join(', ')}</div>
      )}
    </div>
  )
}
