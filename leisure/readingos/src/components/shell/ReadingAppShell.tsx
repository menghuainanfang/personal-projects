import { useEffect, useState, type ReactNode } from 'react';
import { ActionIcon, AppShell, Group, ScrollArea, Tooltip, useAppShellResize } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { BookOpen, Menu, Search, Sun, Moon, PanelRight, X, ArrowLeft, Play } from 'lucide-react';
import { Modal } from '../../Modal';
import { type Book, type Snapshot } from '../../domain';
import { ReadingNavigation } from './ReadingNavigation';
import { ReadingContextPanel } from './ReadingContextPanel';
export function ReadingAppShell({ view, data, book, theme, setTheme, navigate, openBook, resume, journal, source, children }: {
  view: string; data: Snapshot; book?: Book; theme: string; setTheme: (theme: string) => void; navigate: (view: string) => void;
  openBook: (id: string) => void; resume: () => void; journal: (id: string) => void; source: (id: string) => void; children: ReactNode;
}) {
  const small = useMediaQuery('(max-width: 960px)');
  const [navigation, setNavigation] = useState(true), [context, setContext] = useState(false), [search, setSearch] = useState(false), [query, setQuery] = useState('');
  useEffect(() => { setNavigation(!small); }, [small]);
  const resize = useAppShellResize({ aside: { min: 240, max: 380, label: '调整书籍上下文宽度' }, initialSizes: JSON.parse(localStorage.getItem('readingos.workspace.sizes') || '{}'), onResizeEnd: sizes => localStorage.setItem('readingos.workspace.sizes', JSON.stringify(sizes)) });
  const contextVisible = context && !!book && view === 'book';
  const icon = (label: string, child: ReactNode, action: () => void) => <Tooltip label={label}><ActionIcon variant="subtle" aria-label={label} onClick={action} size="lg">{child}</ActionIcon></Tooltip>;
  const titles: Record<string,string> = { library: '我的书库', book: book?.title || '阅读档案', insights: '洞见与实践', goals: '阅读计划', settings: '资料与设置' };
  return <AppShell className="workspace-root" header={{ height: 56 }} navbar={{ width: 210, breakpoint: 960, collapsed: { mobile: !navigation, desktop: !navigation } }} aside={{ width: 288, breakpoint: 1200, collapsed: { mobile: !contextVisible, desktop: !contextVisible } }} resize={resize} transitionDuration={120} zIndex={40}>
    <AppShell.Header><Group justify="space-between" h="100%" px="md" wrap="nowrap">
      <Group gap="xs" wrap="nowrap">{icon(navigation ? '收起导航' : '展开导航', <Menu size={19} />, () => setNavigation(!navigation))}{view === 'book' && icon('回到书库', <ArrowLeft size={18} />, () => navigate('library'))}<span className="workspace-location">{titles[view]}</span></Group>
      <Group gap={4} wrap="nowrap">{icon('寻找书籍', <Search size={19} />, () => setSearch(true))}{data.assets.length > 0 && icon('继续上次阅读', <Play size={18} />, resume)}{view === 'book' && icon(contextVisible ? '隐藏书籍上下文' : '显示书籍上下文', <PanelRight size={19} />, () => setContext(!context))}{icon(theme === 'light' ? '深色主题' : '浅色主题', theme === 'light' ? <Moon size={19} /> : <Sun size={19} />, () => setTheme(theme === 'light' ? 'dark' : 'light'))}</Group>
    </Group></AppShell.Header>
    <AppShell.Navbar className="workspace-navigation" p="md"><AppShell.Section><div className="workspace-brand"><BookOpen size={25}/><div>ReadingOS<small>为阅读留一处空间</small></div></div></AppShell.Section><AppShell.Section grow component={ScrollArea} type="auto"><ReadingNavigation view={view} count={data.books.length} navigate={value => { navigate(value); if(small) setNavigation(false); }}/></AppShell.Section><AppShell.Section><p className="workspace-offline">本地书库 · 离线可用</p></AppShell.Section></AppShell.Navbar>
    <AppShell.Main className="workspace-main"><div className={'main-area '+(view === 'book' ? 'book-home' : '')}>{children}</div></AppShell.Main>
    {contextVisible && book && <AppShell.Aside className="workspace-context" aria-label="书籍上下文"><AppShell.Section p="sm"><Group justify="space-between"><strong>书籍上下文</strong>{icon('关闭书籍上下文', <X size={18}/>, () => setContext(false))}</Group></AppShell.Section><AppShell.Section grow component={ScrollArea} p="md"><ReadingContextPanel book={book} data={data} journal={id => { setContext(false); journal(id); }} source={id => { setContext(false); source(id); }}/></AppShell.Section></AppShell.Aside>}
    {search && <Modal title="寻找书籍" onClose={() => setSearch(false)} onSubmit={e => e.preventDefault()}><label>书名、作者或标签<input autoFocus aria-label="全局寻找书籍" value={query} onChange={e => setQuery(e.target.value)}/></label><div className="workspace-search-results">{data.books.filter(b => (b.title+' '+b.author+' '+b.tags).toLowerCase().includes(query.toLowerCase())).map(b => <button type="button" key={b.id} onClick={() => { setSearch(false); openBook(b.id); }}>{b.title}<small>{b.author}</small></button>)}</div></Modal>}
  </AppShell>;
}
