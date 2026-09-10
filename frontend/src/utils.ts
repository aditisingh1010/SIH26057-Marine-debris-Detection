import type { Detection, RiskLevel } from './types'

export function getRiskLevel(detection: Detection): RiskLevel {
  if (detection.risk_level) {
    const r = detection.risk_level.toLowerCase()
    if (r === 'critical') return 'Critical'
    if (r === 'high') return 'High'
    if (r === 'medium') return 'Medium'
    if (r === 'low') return 'Low'
  }
  const cls = (detection.class || '').toLowerCase()
  if (
    cls.includes('ghost_pot') ||
    cls.includes('hazard') ||
    cls.includes('mine') ||
    cls.includes('net')
  ) {
    return 'Critical'
  }
  if (
    cls.includes('wreck') ||
    cls.includes('shipwreck') ||
    cls.includes('container') ||
    cls.includes('explosive')
  ) {
    return 'High'
  }
  if (detection.confidence >= 0.7) {
    return 'High'
  }
  if (detection.confidence >= 0.4) {
    return 'Medium'
  }
  return 'Low'
}

export function getRiskBadgeClass(level: RiskLevel): string {
  switch (level) {
    case 'Critical':
      return 'badge-risk critical'
    case 'High':
      return 'badge-risk high'
    case 'Medium':
      return 'badge-risk medium'
    case 'Low':
      return 'badge-risk low'
    default:
      return 'badge-risk'
  }
}

export interface ModelModeInfo {
  isMock: boolean
  badgeLabel: string
  fullName: string
}

export function getModelMode(inferenceMode?: string | null, modelName?: string | null): ModelModeInfo {
  // Use inference_mode as the authoritative signal
  const isMock = !inferenceMode || inferenceMode.toLowerCase() === 'mock'

  if (isMock) {
    return {
      isMock: true,
      badgeLabel: 'Mock Mode',
      fullName: 'Mock Simulation Mode',
    }
  }

  const cleanName = (modelName || 'best.pt').trim()
  const displayModel = cleanName

  return {
    isMock: false,
    badgeLabel: `Real model: ${cleanName}`,
    fullName: displayModel,
  }
}

export function formatConfidence(conf: number): string {
  return `${(conf * 100).toFixed(1)}%`
}

export function formatGeoStatus(status: string): string {
  switch (status) {
    case 'computed':
      return 'Approximate (pixel + heading)'
    case 'survey_position_only':
      return 'Survey position only'
    case 'unavailable':
      return 'Unavailable (no metadata)'
    default:
      return status.replace(/_/g, ' ')
  }
}
