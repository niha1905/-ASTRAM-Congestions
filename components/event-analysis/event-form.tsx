'use client'

import { Loader2, Play } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { EventInput, Priority } from '@/lib/types'

const EVENT_TYPES = ['Concert', 'Sports', 'Exhibition', 'Parade', 'Political Rally', 'Festival']
const ZONES = ['Central', 'North', 'South', 'East', 'West']
const CORRIDORS = ['MG Road Corridor', 'Outer Ring Road', 'Hosur Road', 'Bellary Road']
const WEATHER = ['Clear', 'Cloudy', 'Rain', 'Heavy Rain']
const PRIORITIES: Priority[] = ['critical', 'high', 'medium', 'low']

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  )
}

export function EventForm({
  onAnalyze,
  loading,
}: {
  onAnalyze: (input: EventInput) => void
  loading: boolean
}) {
  const [form, setForm] = useState<EventInput>({
    eventName: 'Stadium Concert — Coldplay',
    eventType: 'Concert',
    zone: 'Central',
    corridor: 'MG Road Corridor',
    attendance: 42000,
    weather: 'Clear',
    priority: 'critical',
    date: '2026-06-20',
    time: '18:30',
  })

  const set = <K extends keyof EventInput>(key: K, value: EventInput[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  return (
    <form
      className="glass space-y-4 rounded-xl p-5"
      onSubmit={(e) => {
        e.preventDefault()
        onAnalyze(form)
      }}
    >
      <div>
        <h2 className="text-sm font-semibold">Event Input</h2>
        <p className="text-xs text-muted-foreground">Configure the event parameters to analyze.</p>
      </div>

      <Field label="Event Name">
        <Input value={form.eventName} onChange={(e) => set('eventName', e.target.value)} className="bg-muted/40" />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Event Type">
          <Select value={form.eventType} onValueChange={(v) => v && set('eventType', v)}>
            <SelectTrigger className="bg-muted/40"><SelectValue /></SelectTrigger>
            <SelectContent>
              {EVENT_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Zone">
          <Select value={form.zone} onValueChange={(v) => v && set('zone', v)}>
            <SelectTrigger className="bg-muted/40"><SelectValue /></SelectTrigger>
            <SelectContent>
              {ZONES.map((z) => <SelectItem key={z} value={z}>{z}</SelectItem>)}
            </SelectContent>
          </Select>
        </Field>
      </div>

      <Field label="Corridor">
        <Select value={form.corridor} onValueChange={(v) => v && set('corridor', v)}>
          <SelectTrigger className="bg-muted/40"><SelectValue /></SelectTrigger>
          <SelectContent>
            {CORRIDORS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Attendance">
          <Input
            type="number"
            value={form.attendance}
            onChange={(e) => set('attendance', Number(e.target.value))}
            className="bg-muted/40"
          />
        </Field>
        <Field label="Weather">
          <Select value={form.weather} onValueChange={(v) => v && set('weather', v)}>
            <SelectTrigger className="bg-muted/40"><SelectValue /></SelectTrigger>
            <SelectContent>
              {WEATHER.map((w) => <SelectItem key={w} value={w}>{w}</SelectItem>)}
            </SelectContent>
          </Select>
        </Field>
      </div>

      <Field label="Priority">
        <Select value={form.priority} onValueChange={(v) => v && set('priority', v as Priority)}>
          <SelectTrigger className="bg-muted/40 capitalize"><SelectValue /></SelectTrigger>
          <SelectContent>
            {PRIORITIES.map((p) => <SelectItem key={p} value={p} className="capitalize">{p}</SelectItem>)}
          </SelectContent>
        </Select>
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Date">
          <Input type="date" value={form.date} onChange={(e) => set('date', e.target.value)} className="bg-muted/40" />
        </Field>
        <Field label="Time">
          <Input type="time" value={form.time} onChange={(e) => set('time', e.target.value)} className="bg-muted/40" />
        </Field>
      </div>

      <Button type="submit" className="w-full gap-2" disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
        {loading ? 'Analyzing…' : 'Analyze Event'}
      </Button>
    </form>
  )
}
