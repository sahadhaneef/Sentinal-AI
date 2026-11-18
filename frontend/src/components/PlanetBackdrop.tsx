import { useEffect, useRef, useState } from 'react';
import { useLandingReducedMotion } from './LandingMotion';

const vertex = `attribute vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }`;

// Procedural globe: no remote textures, external model requests, or CDN runtime.
const fragment = `precision highp float;
uniform vec2 resolution;
uniform float time;
uniform float progress;
uniform float lightMode;
float hash(vec3 p) { return fract(sin(dot(p, vec3(127.1,311.7,74.7))) * 43758.5453); }
float noise(vec3 p) {
  vec3 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),
                 mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),
                 mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float fbm(vec3 p) { float n=0.0, a=0.5; for(int i=0;i<4;i++){ n+=a*noise(p);p=p*2.03+4.7;a*=0.5; } return n; }
float segment(float p, float a, float b) { return smoothstep(a,b,p); }
void main() {
  vec2 uv=gl_FragCoord.xy/resolution;
  float aspect=resolution.x/resolution.y;
  float a=segment(progress,0.0,0.32), b=segment(progress,0.32,0.64), c=segment(progress,0.64,1.0);
  float lateral=clamp(aspect/1.5,0.35,1.0);
  vec2 center=vec2(0.50+(-0.33*a+0.66*b-0.33*c)*lateral, -0.38+0.89*a-0.02*b-0.04*c);
  float radius=0.90-0.57*a-0.02*b+0.07*c;
  vec2 q=(uv-center)*vec2(aspect,1.0);
  float d=length(q)/radius;
  vec3 bg=mix(vec3(0.016,0.030,0.068),vec3(0.94,0.965,0.99),lightMode);
  bg+=vec3(0.015,0.055,0.095)*exp(-length((uv-vec2(0.75,0.2))*vec2(aspect,1.0))*3.0);
  // Stars have stable positions and subtle luminance variation.
  vec2 grid=uv*vec2(aspect*120.0,120.0);
  vec2 cell=floor(grid), local=fract(grid)-0.5;
  float seed=hash(vec3(cell,3.0));
  float star=step(0.978,seed)*exp(-dot(local,local)*180.0)*(0.65+0.35*sin(time*0.6+seed*80.0));
  bg+=mix(vec3(0.48,0.69,0.95),vec3(-0.18,-0.12,-0.03),lightMode)*star*0.5;
  float halo=exp(-abs(d-1.0)*18.0);
  bg+=vec3(0.10,0.43,0.64)*halo*0.46;
  if(d<1.0) {
    vec3 n=vec3(q/radius,sqrt(max(0.0,1.0-d*d)));
    float angle=time*0.035+progress*5.0265+2.07;
    float co=cos(angle), si=sin(angle);
    vec3 p=vec3(co*n.x+si*n.z,n.y,-si*n.x+co*n.z);
    float tilt=0.37; p=vec3(p.x,cos(tilt)*p.y-sin(tilt)*p.z,sin(tilt)*p.y+cos(tilt)*p.z);
    float terrain=fbm(p*3.6);
    float land=smoothstep(0.47,0.53,terrain);
    float detail=fbm(p*22.0);
    vec3 ocean=mix(vec3(0.012,0.055,0.14),vec3(0.025,0.20,0.29),noise(p*5.0+time*0.015));
    vec3 ground=mix(vec3(0.05,0.17,0.17),vec3(0.19,0.39,0.30),detail);
    vec3 sun=normalize(vec3(-0.8,0.65,1.0));
    float light=max(dot(n,sun),0.0);
    vec3 surface=mix(ocean,ground,land)*(0.12+light*1.12);
    float clouds=smoothstep(0.56,0.73,fbm(p*6.0+vec3(time*0.013,0.0,time*0.006)));
    surface=mix(surface,vec3(0.63,0.79,0.87)*(0.25+light*0.75),clouds*0.62);
    float glint=pow(max(dot(reflect(-sun,n),vec3(0,0,1)),0.0),44.0)*(1.0-land);
    surface+=vec3(0.45,0.76,0.85)*glint*0.40;
    float cities=step(0.77,noise(p*100.0))*step(0.45,terrain)*(1.0-smoothstep(0.10,0.60,light));
    surface+=vec3(1.0,0.66,0.26)*cities*0.65;
    float rim=pow(1.0-n.z,3.0);
    surface+=vec3(0.14,0.68,0.85)*rim*0.75;
    // Fine longitude/latitude arcs evoke a secure, connected system.
    float longitude=atan(p.z,p.x), latitude=asin(clamp(p.y,-1.0,1.0));
    float lines=pow(1.0-abs(sin(longitude*12.0)),70.0)+pow(1.0-abs(sin(latitude*10.0)),70.0);
    surface+=vec3(0.10,0.40,0.45)*lines*0.09;
    surface=mix(surface,surface*1.1+vec3(0.025,0.04,0.05),lightMode);
    bg=mix(bg,surface,1.0-smoothstep(0.993,1.0,d));
  }
  gl_FragColor=vec4(bg,1.0);
}`;

export function PlanetBackdrop({ running }: { running: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const reduce = useLandingReducedMotion();
  const [contextVersion, setContextVersion] = useState(0);
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const gl = element.getContext('webgl', { alpha: false, antialias: false, powerPreference: 'low-power', preserveDrawingBuffer: true });
    if (!gl) { element.dataset.renderer = 'fallback'; return; }
    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      gl.shaderSource(shader, source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) { gl.deleteShader(shader); return null; }
      return shader;
    };
    const vs = compile(gl.VERTEX_SHADER, vertex), fs = compile(gl.FRAGMENT_SHADER, fragment);
    const program = gl.createProgram();
    if (!vs || !fs || !program) {
      if (vs) gl.deleteShader(vs); if (fs) gl.deleteShader(fs); if (program) gl.deleteProgram(program);
      element.dataset.renderer = 'fallback'; return;
    }
    gl.attachShader(program, vs); gl.attachShader(program, fs); gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      gl.deleteProgram(program); gl.deleteShader(vs); gl.deleteShader(fs);
      element.dataset.renderer = 'fallback'; return;
    }
    gl.useProgram(program);
    const buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const size = gl.getUniformLocation(program, 'resolution');
    const clock = gl.getUniformLocation(program, 'time');
    const scroll = gl.getUniformLocation(program, 'progress');
    const mode = gl.getUniformLocation(program, 'lightMode');
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0, last = 0, elapsed = 0, current = 0, target = 0;
    let lost = false;
    const draw = () => {
      gl.uniform2f(size, element.width, element.height);
      gl.uniform1f(clock, elapsed); gl.uniform1f(scroll, current);
      gl.uniform1f(mode, document.documentElement.dataset.theme === 'light' ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    };
    const updateScroll = () => {
      const page = element.closest('.premium-landing');
      if (!page) return;
      const rect = page.getBoundingClientRect();
      target = Math.min(1, Math.max(0, -rect.top / Math.max(1, rect.height - innerHeight)));
    };
    const tick = (now: number) => {
      if (now - last >= 33) {
        const dt = Math.min((now-last)/1000,0.05); last=now;
        elapsed+=dt; current+=(target-current)*Math.min(1,dt*4.5); draw();
      }
      frame=requestAnimationFrame(tick);
    };
    const sync = () => {
      cancelAnimationFrame(frame);
      if (lost) return;
      if (reduce || media.matches) { current=0; elapsed=0; }
      draw();
      if (running && !reduce && !media.matches) { last=performance.now(); frame=requestAnimationFrame(tick); }
    };
    const resize = () => {
      // Bound fragment work independently of high-DPI monitor size.
      const ratio=Math.min(devicePixelRatio || 1, 1, 1000/innerWidth, 700/innerHeight);
      element.width=Math.round(innerWidth*ratio); element.height=Math.round(innerHeight*ratio);
      gl.viewport(0,0,element.width,element.height); updateScroll(); draw();
    };
    const lose = (event: Event) => { event.preventDefault(); lost=true; cancelAnimationFrame(frame); element.dataset.renderer='fallback'; };
    const restore = () => setContextVersion((version) => version + 1);
    element.addEventListener('webglcontextlost',lose);
    element.addEventListener('webglcontextrestored',restore);
    element.dataset.renderer='webgl';
    resize(); sync();
    const themeObserver = new MutationObserver(() => { if (!lost) draw(); });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    window.addEventListener('resize',resize); window.addEventListener('scroll',updateScroll,{passive:true});
    media.addEventListener('change',sync);
    return () => {
      cancelAnimationFrame(frame);
      themeObserver.disconnect();
      window.removeEventListener('resize',resize); window.removeEventListener('scroll',updateScroll);
      media.removeEventListener('change',sync);
      element.removeEventListener('webglcontextlost',lose); element.removeEventListener('webglcontextrestored',restore);
      gl.deleteBuffer(buffer); gl.deleteProgram(program); gl.deleteShader(vs); gl.deleteShader(fs);
    };
  }, [running, reduce, contextVersion]);
  return <><div className="planet-fallback" /><canvas ref={canvas} className="planet-canvas" aria-hidden="true" /></>;
}
