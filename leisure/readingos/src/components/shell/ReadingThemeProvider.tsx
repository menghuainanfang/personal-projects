import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { createTheme, MantineProvider } from '@mantine/core';
const ThemeContext = createContext({ theme: 'light', setTheme: (_theme: string) => {} });
const theme = createTheme({
  primaryColor: 'pine', primaryShade: { light: 6, dark: 2 }, defaultRadius: 'sm',
  colors: { pine: ['#f4f6ef','#e2e8dd','#b5c9ae','#a0b49b','#83977f','#697e67','#526554','#425645','#354736','#28382a'] },
  fontFamily: '"Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif',
  fontSizes: { xs: '12px', sm: '13px', md: '14px', lg: '16px', xl: '20px' },
  radius: { xs: '4px', sm: '6px', md: '8px', lg: '10px', xl: '12px' },
});
export function ReadingThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setTheme] = useState(localStorage.getItem('readingos.theme') || 'light');
  useEffect(() => { document.documentElement.dataset.theme = mode; localStorage.setItem('readingos.theme', mode); }, [mode]);
  return <ThemeContext.Provider value={{ theme: mode, setTheme }}><MantineProvider theme={theme} forceColorScheme={mode === 'dark' ? 'dark' : 'light'}>{children}</MantineProvider></ThemeContext.Provider>;
}
export const useReadingTheme = () => useContext(ThemeContext);
