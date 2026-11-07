/* Execute a flat translated payload in an independent Musashi 68020 core.
 * This checks native code, native-endian planar composition and exact PCM
 * execution. Its core-cycle count is not Amiga timing or a hardware benchmark. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "m68k.h"
static uint8_t mem[0x1000000];
static uint32_t meta[32];
static int done;
static unsigned frames,checked;
static uint64_t core_cycles;
static FILE *states;
static uint8_t record[4392];
static int have_record;
enum { TABS,INIT,ROM,RUN,RT,NES,AR_ENABLE,HW_ENABLE,FATAL,HOOK_INIT,HOOK_FRAME,HOOK_INPUT,LAYOUT,PCM_HASH };
unsigned int m68k_read_memory_8(unsigned int a){ return mem[a&0xffffff]; }
unsigned int m68k_read_memory_16(unsigned int a){ return (m68k_read_memory_8(a)<<8)|m68k_read_memory_8(a+1); }
unsigned int m68k_read_memory_32(unsigned int a){ return (m68k_read_memory_16(a)<<16)|m68k_read_memory_16(a+2); }
void m68k_write_memory_8(unsigned int a,unsigned int v){ mem[a&0xffffff]=(uint8_t)v; }
void m68k_write_memory_16(unsigned int a,unsigned int v){ m68k_write_memory_8(a,v>>8); m68k_write_memory_8(a+1,v); }
void m68k_write_memory_32(unsigned int a,unsigned int v){ m68k_write_memory_16(a,v>>16); m68k_write_memory_16(a+2,v); }
unsigned int m68k_read_disassembler_8(unsigned int a){ return m68k_read_memory_8(a); }
unsigned int m68k_read_disassembler_16(unsigned int a){ return m68k_read_memory_16(a); }
unsigned int m68k_read_disassembler_32(unsigned int a){ return m68k_read_memory_32(a); }
static void next_record(void){
    size_t n=fread(record,1,sizeof record,states);
    if(n && n!=sizeof record){ fprintf(stderr,"Truncated state record\n"); exit(2); }
    have_record=(n==sizeof record);
}
static uint64_t le64(const uint8_t*p){ uint64_t v=0;for(int i=7;i>=0;i--)v=(v<<8)|p[i];return v; }
static void hook(unsigned int pc){
    if(pc==0x1fe000){ done=1;m68k_end_timeslice();return; }
    if(pc==meta[HOOK_FRAME]){
        uint32_t sp=m68k_get_reg(NULL,M68K_REG_SP),f=m68k_read_memory_32(sp+4);
        frames++;
        if(have_record && le64(record)==f){
            unsigned off[4]={8,2056,2312,2344},len[4]={2048,256,32,2048};
            const char*name[4]={"RAM","OAM","palette","nametables"};
            for(int i=0;i<4;i++){
                unsigned field=m68k_read_memory_32(meta[LAYOUT]+4*(3+i));
                if(memcmp(mem+meta[NES]+field,record+off[i],len[i])){
                    fprintf(stderr,"Native mismatch: frame %u %s\n",f,name[i]); exit(5);
                }
            }
            checked++; next_record();
        }
        if(frames%1000==0){ printf("native frames %u\n",frames);fflush(stdout); }
    }
    if(pc==meta[FATAL] || pc<0x1000){ fprintf(stderr,"Native exception PC=%08x\n",pc);exit(3); }
}
static void call(uint32_t fn,uint32_t a,uint32_t b){
    uint32_t sp=0x9ff000;
    m68k_write_memory_32(sp,0x1fe000);m68k_write_memory_32(sp+4,a);m68k_write_memory_32(sp+8,b);
    m68k_set_reg(M68K_REG_SR,0x2700);m68k_set_reg(M68K_REG_SP,sp);m68k_set_reg(M68K_REG_PC,fn);
    done=0;
    while(!done){ core_cycles+=(unsigned)m68k_execute(100000); }
}
static void load(const char*p,unsigned base){
    FILE*f=fopen(p,"rb");if(!f){perror(p);exit(2);}
    size_t n=fread(mem+base,1,sizeof mem-base,f);if(fgetc(f)!=EOF){fprintf(stderr,"Image too large\n");exit(2);}fclose(f);
    if(!n){fprintf(stderr,"Empty image\n");exit(2);}
}
int main(int argc,char**argv){
    if(argc!=6){fprintf(stderr,"usage: native_cpu payload.bin hooks.bin metadata.bin states.bin frames\n");return 2;}
    load(argv[1],0x200000);load(argv[2],0xa00000);
    FILE*f=fopen(argv[3],"rb");if(!f){perror(argv[3]);return 2;}
    for(int i=0;i<=PCM_HASH;i++){uint8_t b[4];if(fread(b,1,4,f)!=4)return 2;meta[i]=(uint32_t)b[0]<<24|(uint32_t)b[1]<<16|(uint32_t)b[2]<<8|b[3];}fclose(f);
    states=fopen(argv[4],"rb");if(!states){perror(argv[4]);return 2;}next_record();
    m68k_init();m68k_set_cpu_type(M68K_CPU_TYPE_68020);m68k_set_instr_hook_callback(hook);
    m68k_write_memory_32(0,0x9ff000);m68k_write_memory_32(4,0x200000);m68k_pulse_reset();
    call(meta[TABS],0,0);
    m68k_write_memory_32(meta[AR_ENABLE],1);m68k_write_memory_32(meta[HW_ENABLE],1);
    call(meta[INIT],meta[ROM],meta[ROM]+131072);call(meta[HOOK_INIT],0,0);
    unsigned layout=meta[LAYOUT];
    m68k_write_memory_32(meta[RT]+m68k_read_memory_32(layout),meta[HOOK_FRAME]);
    m68k_write_memory_32(meta[RT]+m68k_read_memory_32(layout+4),meta[HOOK_INPUT]);
    call(meta[RUN],(uint32_t)strtoul(argv[5],0,10),0);
    if(have_record){fprintf(stderr,"Not all expected checkpoints executed\n");return 5;}
    printf("{\"native_frames\":%u,\"checkpoints\":%u,\"pcm_fnv32\":%u,\"core_cycles\":%llu,\"amiga_speed_certified\":false}\n",frames,checked,m68k_read_memory_32(meta[PCM_HASH]),(unsigned long long)core_cycles);
    return 0;
}
