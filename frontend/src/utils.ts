import type { Detection, RiskLevel } from './types'

export function getRiskLevel(detection: Detection): RiskLevel {
  if (detection.risk_level) {
    const r = detection.risk_level.toLowerCase()
    if (r === 'high' || r === 'critical') return 'High'
    if (r === 'medium') return 'Medium'
    if (r === 'low') return 'Low'
  }
  const cls = detection.class.toLowerCase()
  if (
    cls.includes('hazard') ||
    cls.includes('mine') ||
    cls.includes('net') ||
    cls.includes('chemical') ||
    cls.includes('container') ||
    cls.includes('wreck') ||
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
    case 'High':
      return 'risk-badge risk-high'
    case 'Medium':
      return 'risk-badge risk-medium'
    case 'Low':
      return 'risk-badge risk-low'
    default:
      return 'risk-badge'
  }
}

export interface ModelModeInfo {
  isMock: boolean
  badgeLabel: string
  fullName: string
}

export function getModelMode(modelName?: string | null): ModelModeInfo {
  if (!modelName || modelName.toLowerCase().includes('mock') || modelName.toLowerCase().includes('dummy')) {
    return {
      isMock: true,
      badgeLabel: 'Mock Mode',
      fullName: 'Mock Simulation Mode',
    }
  }

  const cleanName = modelName.trim()
  const isYolo = cleanName.toLowerCase().includes('yolo')
  const displayModel = isYolo ? cleanName : `YOLOv8n (${cleanName})`

  return {
    isMock: false,
    badgeLabel: 'Real Model: YOLOv8n',
    fullName: displayModel,
  }
}

export function formatConfidence(conf: number): string {
  return `${(conf * 100).toFixed(1)}%`
}

export function formatGeoStatus(status: string): string {
  switch (status) {
    case 'computed':
      return 'Exact (Ray-traced)'
    case 'survey_position_only':
      return 'Survey Position (Nadir)'
    case 'unavailable':
      return 'Unavailable (No metadata)'
    default:
      return status.replace(/_/g, ' ')
  }
}
