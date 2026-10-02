/* SPDX-License-Identifier: MIT. Dependency-free tests for optional pose library. */
'use strict';
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../shared/narrative-motion.js'),'utf8'),context);
const N=context.window.NarrativeMotion;
assert.equal(N.cutaway(-1).clipPath,'inset(0 100% 0 0)');
assert.equal(N.cutaway(9).clipPath,'inset(0 0% 0 0)');
assert.equal(N.cutaway(9,{reverse:true}).clipPath,'inset(0 100% 0 0)');
assert.equal(N.cutaway(9,{axis:'y'}).clipPath,'inset(0 0 0% 0)');
assert.equal(N.lens(9).clipPath,'circle(35% at 50% 50%)');
assert.equal(N.focus(9).filter,'blur(0px)');
assert.equal(N.focus(-1).filter,'blur(12px)');
const opts={start:1,duration:2,points:[[20,30],[40,10],[70,90],[110,120]]};
assert.equal(N.converge(-1,opts).x,20);assert.equal(N.converge(20,opts).y,120);
assert.equal(N.converge(2,opts).x,57.5);
for(const name of ['cutaway','lens','focus','converge','perspective']){
 const baseline=JSON.stringify(N[name](.47));
 for(const t of [9,0,.8,4,-20])N[name](t);
 assert.equal(JSON.stringify(N[name](.47)),baseline,`${name}: seek-dependent state`);
 assert(!baseline.includes('NaN'));assert(!baseline.includes('Infinity'));
}
assert.equal(N.perspective(9).transform,'perspective(900px) translate3d(0px,0px,0px) rotateX(0deg) rotateY(0deg)');
console.log('PASS narrative-motion: endpoints, clamping, forward/reverse masks, Bézier midpoint, out-of-order sampling');
