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
static uint64_t *profile, profile_time;
static unsigned profile_pc,profile_first,profile_last;
static int profile_active;
static FILE *states, *state_out;
static unsigned mismatches;
static int diagnose;
static uint8_t record[4392];
static int have_record;
enum { TABS,INIT,ROM,RUN,RT,NES,AR_ENABLE,HW_ENABLE,FATAL,HOOK_INIT,HOOK_FRAME,HOOK_INPUT,LAYOUT,PCM_HASH,CACHE_STATS,HW_SETMEM,HW_MEM,HW_BYTES,HW_EXPECTED };
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
static void write_state(const void *p,size_t n){
    if(fwrite(p,1,n,state_out)!=n){perror("native state output");exit(2);}
}
static uint64_t le64(const uint8_t*p){ uint64_t v=0;for(int i=7;i>=0;i--)v=(v<<8)|p[i];return v; }
static void hook(unsigned int pc){
    if(profile){
        uint64_t now=core_cycles+(unsigned)m68k_cycles_run();
        if(profile_active) profile[(profile_pc&0xffffff)>>1]+=now-profile_time;
        profile_time=now;profile_pc=pc;
    }
    if(pc==0x1fe000){ done=1;m68k_end_timeslice();return; }
    if(pc==meta[HOOK_FRAME]){
        uint32_t sp=m68k_get_reg(NULL,M68K_REG_SP),f=m68k_read_memory_32(sp+4);
        frames++;
        if(state_out){
            uint8_t header[8];for(unsigned j=0;j<8;j++)header[j]=(uint8_t)((uint64_t)f>>(8*j));
            write_state(header,8);
            const unsigned lengths[4]={2048,256,32,2048};
            for(unsigned j=0;j<4;j++){
                unsigned field=m68k_read_memory_32(meta[LAYOUT]+4*(3+j));
                write_state(mem+meta[NES]+field,lengths[j]);
            }
        }
        if(have_record && le64(record)==f){
            unsigned off[4]={8,2056,2312,2344},len[4]={2048,256,32,2048};
            const char*name[4]={"RAM","OAM","palette","nametables"};
            for(int i=0;i<4;i++){
                unsigned field=m68k_read_memory_32(meta[LAYOUT]+4*(3+i));
                if(memcmp(mem+meta[NES]+field,record+off[i],len[i])){
                    mismatches++;
                    if(mismatches<=16){
                    fprintf(stderr,"Native mismatch: frame %u %s\n",f,name[i]);
                    for(unsigned j=0;j<len[i];j++) if(mem[meta[NES]+field+j]!=record[off[i]+j])
                        fprintf(stderr,"  offset %04x native %02x host %02x\n",j,mem[meta[NES]+field+j],record[off[i]+j]);
                    }
                    if(!diagnose) exit(5);
                }
            }
            checked++; next_record();
        }
        if(frames%1000==0){ printf("native frames %u\n",frames);fflush(stdout); }
    }
    if(pc==meta[FATAL] || pc<0x1000){ fprintf(stderr,"Native exception PC=%08x\n",pc);exit(3); }
    profile_active=profile && frames>=profile_first && frames<profile_last;
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
    for(int i=0;i<=HW_EXPECTED;i++){uint8_t b[4];if(fread(b,1,4,f)!=4)return 2;meta[i]=(uint32_t)b[0]<<24|(uint32_t)b[1]<<16|(uint32_t)b[2]<<8|b[3];}fclose(f);
    diagnose=getenv("NATIVE_DIAGNOSE_MISMATCHES")!=NULL;
    if(getenv("NATIVE_STATEOUT")){state_out=fopen(getenv("NATIVE_STATEOUT"),"wb");if(!state_out){perror("native state output");return 2;}}
    states=fopen(argv[4],"rb");if(!states){perror(argv[4]);return 2;}next_record();
    const char *profile_path=getenv("NATIVE_PROFILE");
    if(profile_path){
        profile=calloc(0x800000,sizeof *profile);
        if(!profile){perror("profile allocation");return 2;}
        profile_first=getenv("NATIVE_PROFILE_FIRST")?(unsigned)atoi(getenv("NATIVE_PROFILE_FIRST")):1600;
        profile_last=getenv("NATIVE_PROFILE_LAST")?(unsigned)atoi(getenv("NATIVE_PROFILE_LAST")):2200;
        if(profile_first>=profile_last || profile_last>(unsigned)strtoul(argv[5],0,10)) return 2;
    }
    m68k_init();m68k_set_cpu_type(M68K_CPU_TYPE_68020);m68k_set_instr_hook_callback(hook);
    m68k_write_memory_32(0,0x9ff000);m68k_write_memory_32(4,0x200000);m68k_pulse_reset();
    if(meta[HW_MEM]<0x1000 || (meta[HW_MEM]&3) || meta[HW_BYTES]<8 ||
       (meta[HW_BYTES]&3) || meta[HW_MEM]>=0x200000 ||
       meta[HW_BYTES]>0x200000-meta[HW_MEM] ||
       meta[HW_EXPECTED]<0xa00000 || meta[HW_EXPECTED]>sizeof mem-4 ||
       meta[HW_BYTES]!=m68k_read_memory_32(meta[HW_EXPECTED]) ||
       meta[HW_SETMEM]<0x200000 || meta[HW_SETMEM]>=0xa00000){
        fprintf(stderr,"Invalid renderer storage metadata\n");return 2;
    }
    call(meta[TABS],0,0);
    /* Match display_init's ownership order before rt_init derives pointers. */
    call(meta[HW_SETMEM],meta[HW_MEM],0);
    m68k_write_memory_32(meta[AR_ENABLE],1);m68k_write_memory_32(meta[HW_ENABLE],1);
    call(meta[INIT],meta[ROM],meta[ROM]+131072);call(meta[HOOK_INIT],0,0);
    unsigned layout=meta[LAYOUT];
    m68k_write_memory_32(meta[RT]+m68k_read_memory_32(layout),meta[HOOK_FRAME]);
    m68k_write_memory_32(meta[RT]+m68k_read_memory_32(layout+4),meta[HOOK_INPUT]);
    call(meta[RUN],(uint32_t)strtoul(argv[5],0,10),0);
    if(have_record){fprintf(stderr,"Not all expected checkpoints executed\n");return 5;}
    if(profile){
        FILE *pf=fopen(profile_path,"w");if(!pf){perror(profile_path);return 2;}
        fprintf(pf,"pc,core_cycles\n");
        for(unsigned i=0;i<0x800000;i++) if(profile[i]) fprintf(pf,"%x,%llu\n",i*2,(unsigned long long)profile[i]);
        fclose(pf);free(profile);
    }
    printf("{\"native_frames\":%u,\"checkpoints\":%u,\"pcm_fnv32\":%u,\"core_cycles\":%llu,\"amiga_speed_certified\":false",frames,checked,m68k_read_memory_32(meta[PCM_HASH]),(unsigned long long)core_cycles);
    if(meta[CACHE_STATS]){
        printf(",\"sprite_cache\":{");
        const char *keys[4]={"calls","hits","misses","oam_words"};
        for(int i=0;i<4;i++)printf("%s\"%s\":%u",i?",":"",keys[i],m68k_read_memory_32(meta[CACHE_STATS]+4*i));
        printf("}");
    }
    printf(",\"state_mismatches\":%u}\n",mismatches);
    if(state_out && fclose(state_out)){perror("native state output close");return 2;}
    return mismatches?5:0;
}
