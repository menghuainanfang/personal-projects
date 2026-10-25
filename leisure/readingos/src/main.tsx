import { createRoot } from "react-dom/client";
import '@mantine/core/styles.css';
import '@daypicker/react/style.css';
import "./style.css";
import './workspace.css';
import { App } from "./App";
import { ReadingThemeProvider } from './components/shell/ReadingThemeProvider';
createRoot(document.getElementById("root")!).render(<ReadingThemeProvider><App /></ReadingThemeProvider>);
