import { ShieldCheck, Zap, Bot } from 'lucide-react';

export function CodePreviewCard() {
  return (
    <div className="relative h-full flex flex-col items-center justify-center p-8">
      {/* Code/UI Preview Card */}
      <div className="w-full max-w-[380px] bg-white border border-border rounded-xl overflow-hidden shadow-xl shadow-primary/5 transform rotate-1 hover:rotate-0 transition-transform duration-500">
        {/* Fake Window Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/50">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[hsl(var(--destructive-muted)/0.15)] border border-red-500/50" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/20 border border-green-500/50" />
          </div>
          <div className="text-[10px] text-muted-foreground font-mono">
            sandtuari_sync.ts
          </div>
        </div>

        {/* Code Content */}
        <div className="p-5 font-mono text-[11px] leading-relaxed">
          <div className="flex gap-2 text-muted-foreground mb-2">
            <span>// Wearable data sync for clinical follow-up</span>
          </div>
          <div className="text-blue-400">
            const <span className="text-foreground">insight</span> ={' '}
            <span className="text-purple-400">await</span> sandtuariConnect.sync(
            {'{'}
          </div>
          <div className="pl-4 text-foreground/90">
            name: <span className="text-green-400">"Withings Daily Sync"</span>,
          </div>
          <div className="pl-4 text-foreground/90">
            trigger: <span className="text-green-400">"New health data"</span>,
          </div>
          <div className="pl-4 text-foreground/90">
            action: <span className="text-blue-400">async</span> (
            <span className="text-orange-300">data</span>) =&gt; {'{'}
          </div>
          <div className="pl-8 text-foreground/90">
            <span className="text-purple-400">if</span> (data.weight) {'{'}
          </div>
          <div className="pl-12 text-foreground/90">
            <span className="text-purple-400">return</span>{' '}
            <span className="text-green-400">"Update patient timeline"</span>;
          </div>
          <div className="pl-8 text-foreground/90">{'}'}</div>
          <div className="text-foreground/90">{'}'});</div>
        </div>

        {/* Integration Badge */}
          <div className="px-4 py-3 border-t border-border bg-muted/50 flex items-center justify-between">
          <div className="flex -space-x-2">
            <div className="w-5 h-5 rounded-full bg-muted border border-border flex items-center justify-center text-[9px] font-bold text-foreground/90">
              G
            </div>
            <div className="w-5 h-5 rounded-full bg-muted border border-border flex items-center justify-center text-[9px] font-bold text-foreground/90">
              A
            </div>
            <div className="w-5 h-5 rounded-full bg-muted border border-border flex items-center justify-center text-[9px] font-bold text-foreground/90">
              O
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-[9px] text-[hsl(var(--success-muted))]">
            <div className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--success-muted))] animate-pulse" />
            Connected
          </div>
        </div>
      </div>

      {/* Text Content */}
      <div className="mt-8 text-center max-w-[300px]">
        <h2 className="text-base font-medium text-foreground tracking-tight mb-2">
          Datos conectados a Sandtuari
        </h2>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Sincroniza Withings y futuros dispositivos en una capa tecnica segura.
        </p>
        <div className="mt-6 flex items-center justify-center gap-4">
          <div className="flex flex-col items-center gap-1">
            <ShieldCheck className="w-4 h-4 text-muted-foreground" />
            <span className="text-[9px] text-muted-foreground/70">Seguro</span>
          </div>
          <div className="w-px h-6 bg-muted" />
          <div className="flex flex-col items-center gap-1">
            <Zap className="w-4 h-4 text-muted-foreground" />
            <span className="text-[9px] text-muted-foreground/70">Rapido</span>
          </div>
          <div className="w-px h-6 bg-muted" />
          <div className="flex flex-col items-center gap-1">
            <Bot className="w-4 h-4 text-muted-foreground" />
            <span className="text-[9px] text-muted-foreground/70">IA</span>
          </div>
        </div>
      </div>
    </div>
  );
}
