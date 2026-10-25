import { useRef, type ReactNode } from 'react';
import { Popover } from '@mantine/core';
import { CalendarDays } from 'lucide-react';
export function CalendarPopover({ label, opened, setOpened, children }: { label: string; opened: boolean; setOpened: (open: boolean) => void; children: (close: () => void) => ReactNode }) {
  const trigger=useRef<HTMLButtonElement>(null);
  const close=()=>{setOpened(false);requestAnimationFrame(()=>trigger.current?.focus());};
  return <Popover opened={opened} onChange={setOpened} position="bottom-end" withinPortal={false} floatingStrategy="fixed" trapFocus closeOnEscape={false} returnFocus={false} zIndex={170} shadow="sm" transitionProps={{duration:0}}>
    <Popover.Target><button type="button" ref={trigger} aria-label={label} aria-expanded={opened} className="calendar-trigger" onClick={()=>setOpened(!opened)}><CalendarDays size={17}/></button></Popover.Target>
    <Popover.Dropdown className="reading-calendar" data-reading-calendar-open onKeyDown={event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close();}}}>{children(close)}</Popover.Dropdown>
  </Popover>;
}

