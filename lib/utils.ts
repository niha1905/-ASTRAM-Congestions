import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Remove HTML tags from a string and return plain text.
 */
export function stripHtml(html?: string | null): string {
  if (!html) return ''
  try {
    const d = typeof document !== 'undefined' ? document.createElement('div') : null
    if (d) {
      d.innerHTML = html
      return d.textContent || d.innerText || ''
    }
    // fallback server-side: crude removal
    return html.replace(/<[^>]*>/g, '')
  } catch (e) {
    return html.replace(/<[^>]*>/g, '')
  }
}

/**
 * Extract the first href from anchor tags in an HTML string.
 */
export function extractFirstLink(html?: string | null): string | null {
  if (!html) return null
  try {
    if (typeof document !== 'undefined') {
      const d = document.createElement('div')
      d.innerHTML = html
      const a = d.querySelector('a')
      return (a && a.getAttribute('href')) || null
    }
    // server-side fallback: regex
    const m = html.match(/href=["']?([^"' >]+)/i)
    return m ? m[1] : null
  } catch (e) {
    const m = html.match(/href=["']?([^"' >]+)/i)
    return m ? m[1] : null
  }
}
