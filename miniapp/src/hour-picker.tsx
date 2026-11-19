import {useLayoutEffect, useRef} from 'react';
import {ChevronDown, ChevronUp} from 'lucide-react';

const hours = Array.from({length:24}, (_, h) => String(h).padStart(2, '0') + ':00');

export function HourPicker({value, disabled, onChange}: {
  value:string;
  disabled:(hour:string)=>boolean;
  onChange:(hour:string)=>void;
}) {
  const wheel = useRef<HTMLDivElement>(null);
  const timer = useRef<number>();
  const options = ['', ...hours.filter(hour => !disabled(hour))];
  const selected = Math.max(0, options.indexOf(value));
  const optionKey = options.join(',');

  useLayoutEffect(() => {
    const el = wheel.current;
    if (el) el.scrollTop = selected * el.clientHeight;
    return () => window.clearTimeout(timer.current);
  }, [selected, optionKey, value]);

  function move(step:number) {
    const el = wheel.current;
    if (!el) return;
    const index = Math.round(el.scrollTop / el.clientHeight);
    el.scrollTo({top:Math.max(0, Math.min(options.length-1,index+step))*el.clientHeight,
      behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }

  function settle() {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      const el = wheel.current;
      if (!el) return;
      const hour = options[Math.round(el.scrollTop / el.clientHeight)];
      if (hour !== undefined && (!hour || !disabled(hour))) onChange(hour);
    }, 140);
  }

  return <div className="hour-field">
    <span>Boʻsh vaqt</span>
    <div className="hour-control">
      <button type="button" aria-label="Oldingi soat" disabled={selected===0} onClick={()=>move(-1)}><ChevronUp size={16}/></button>
      <div className="hour-wheel" ref={wheel} role="spinbutton" tabIndex={0} aria-label="Boʻsh vaqt"
        aria-valuemin={0} aria-valuemax={options.length-1} aria-valuenow={selected} aria-valuetext={value || 'Istalgan vaqt'}
        onScroll={settle} onKeyDown={e=>{
          const steps:Record<string,number> = {ArrowDown:1, ArrowUp:-1, Home:-options.length, End:options.length};
          if (e.key in steps) {e.preventDefault(); move(steps[e.key]);}
        }}>
        {options.map(hour=><div key={hour} aria-hidden="true">{hour || 'Istalgan vaqt'}</div>)}
      </div>
      <button type="button" aria-label="Keyingi soat" disabled={selected===options.length-1} onClick={()=>move(1)}><ChevronDown size={16}/></button>
    </div>
  </div>;
}
