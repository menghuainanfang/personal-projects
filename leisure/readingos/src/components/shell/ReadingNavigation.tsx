import { NavLink, Stack } from '@mantine/core';
import { Library, Lightbulb, Target, Settings } from 'lucide-react';
export function ReadingNavigation({ view, count, navigate }: { view: string; count: number; navigate: (view: string) => void }) {
  return <Stack gap={6} className="reading-navigation">{[
    { id: 'library', label: '书库', icon: Library }, { id: 'insights', label: '洞见与实践', icon: Lightbulb },
    { id: 'goals', label: '阅读计划', icon: Target }, { id: 'settings', label: '资料与设置', icon: Settings },
  ].map(({ id, label, icon: Icon }) => <NavLink component="button" type="button" key={id} aria-label={label} active={view === id || (id === 'library' && view === 'book')} aria-current={view === id ? 'page' : undefined} label={label} leftSection={<Icon size={18} />} rightSection={id === 'library' ? <small>{count}</small> : undefined} onClick={() => navigate(id)} />)}</Stack>;
}
