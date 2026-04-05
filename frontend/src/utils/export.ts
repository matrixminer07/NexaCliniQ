type CsvPrimitive = string | number | boolean | null | undefined

type CsvRow = Record<string, CsvPrimitive>

function escapeCsvValue(value: CsvPrimitive): string {
  if (value === null || value === undefined) return ''
  const str = String(value)
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

export function downloadCsv(filename: string, rows: CsvRow[]): void {
  if (!rows || rows.length === 0) return
  const headers = Object.keys(rows[0])
  const lines = [
    headers.join(','),
    ...rows.map((row) => headers.map((header) => escapeCsvValue(row[header])).join(',')),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}

export async function downloadSvgAsPng(svg: SVGSVGElement, filename: string): Promise<void> {
  const rect = svg.getBoundingClientRect()
  const width = Math.max(1, Math.round(rect.width))
  const height = Math.max(1, Math.round(rect.height))

  const serialized = new XMLSerializer().serializeToString(svg)
  const svgBlob = new Blob([
    serialized.includes('xmlns="http://www.w3.org/2000/svg"')
      ? serialized
      : serialized.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
  ], { type: 'image/svg+xml;charset=utf-8' })

  const svgUrl = URL.createObjectURL(svgBlob)

  await new Promise<void>((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const context = canvas.getContext('2d')
      if (!context) {
        URL.revokeObjectURL(svgUrl)
        reject(new Error('Canvas context unavailable'))
        return
      }
      context.drawImage(image, 0, 0, width, height)
      canvas.toBlob((blob) => {
        URL.revokeObjectURL(svgUrl)
        if (!blob) {
          reject(new Error('Failed to export PNG'))
          return
        }
        const pngUrl = URL.createObjectURL(blob)
        const anchor = document.createElement('a')
        anchor.href = pngUrl
        anchor.download = filename.endsWith('.png') ? filename : `${filename}.png`
        anchor.click()
        URL.revokeObjectURL(pngUrl)
        resolve()
      }, 'image/png')
    }
    image.onerror = () => {
      URL.revokeObjectURL(svgUrl)
      reject(new Error('Failed to load SVG for export'))
    }
    image.src = svgUrl
  })
}

export async function exportChartAsPng(container: HTMLElement | null, filename: string): Promise<void> {
  const svg = container?.querySelector('svg')
  if (!svg) return
  await downloadSvgAsPng(svg, filename)
}
