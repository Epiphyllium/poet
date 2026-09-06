import { Header } from '../page';
import TraceViewer from './trace-viewer';

export default function TracesPage() {
  return <main className="paper-shell trace-shell"><Header active="traces" /><TraceViewer /></main>;
}
