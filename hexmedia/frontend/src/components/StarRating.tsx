import { useState } from 'react'

type Props = {
  value?: number | null
  max?: number
  onChange?: (n: number) => void
  disabled?: boolean
  size?: number
}

export default function StarRating({ value = 0, max = 5, onChange, disabled, size = 22 }: Props) {
  const [hover, setHover] = useState<number | null>(null)
  const display = hover ?? value ?? 0

  return (
    <div role="radiogroup" aria-label="Rating" className="inline-flex items-center gap-1">
      {Array.from({ length: max }, (_, i) => i + 1).map(n => {
        const filled = n <= display
        return (
          <button
            key={n}
            role="radio"
            aria-checked={n === value}
            disabled={disabled}
            onMouseEnter={() => setHover(n)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(n)}
            onBlur={() => setHover(null)}
            onClick={() => onChange?.(n)}
            className={`p-0.5 rounded ${disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer hover:scale-[1.06] transition-transform'}`}
            title={`${n} star${n > 1 ? 's' : ''}`}
          >
            <svg
              width={size}
              height={size}
              viewBox="0 0 24 24"
              fill={filled ? 'currentColor' : 'none'}
              stroke="currentColor"
              className={filled ? 'text-yellow-500' : 'text-neutral-400'}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M11.48 3.5l2.07 4.2c.14.28.41.47.72.51l4.64.67c.79.11 1.1 1.09.53 1.65l-3.36 3.28c-.23.22-.33.54-.28.86l.79 4.6c.14.79-.69 1.39-1.4 1.02l-4.13-2.17a.95.95 0 00-.88 0l-4.13 2.17c-.7.37-1.54-.23-1.4-1.02l.79-4.6c.06-.31-.05-.64-.28-.86L2.56 10.5c-.57-.56-.26-1.54.53-1.65l4.64-.67c.31-.04.58-.23.72-.51l2.07-4.2c.35-.72 1.39-.72 1.74 0z"
              />
            </svg>
          </button>
        )
      })}
    </div>
  )
}
