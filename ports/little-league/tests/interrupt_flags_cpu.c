/* Tiny independent-core fixture: stop at the generated budget escape, before
 * the successor's first 6502 instruction. No ROM or game runtime is required. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "m68k.h"
static uint8_t mem[65536];
unsigned int m68k_read_memory_8(unsigned int a) { return mem[a & 65535]; }
unsigned int m68k_read_memory_16(unsigned int a) { return m68k_read_memory_8(a)*256 + m68k_read_memory_8(a+1); }
unsigned int m68k_read_memory_32(unsigned int a) { return m68k_read_memory_16(a)*65536 + m68k_read_memory_16(a+2); }
void m68k_write_memory_8(unsigned int a,unsigned int v) { mem[a & 65535]=v; }
void m68k_write_memory_16(unsigned int a,unsigned int v) { m68k_write_memory_8(a,v>>8); m68k_write_memory_8(a+1,v); }
void m68k_write_memory_32(unsigned int a,unsigned int v) { m68k_write_memory_16(a,v>>16); m68k_write_memory_16(a+2,v); }
unsigned int m68k_read_disassembler_8(unsigned int a) { return m68k_read_memory_8(a); }
unsigned int m68k_read_disassembler_16(unsigned int a) { return m68k_read_memory_16(a); }
unsigned int m68k_read_disassembler_32(unsigned int a) { return m68k_read_memory_32(a); }
int main(int argc,char **argv) {
    if (argc!=8) return 2;
    FILE *f=fopen(argv[1],"rb"); if (!f) return 2;
    size_t n=fread(mem+0x1000,1,0x1000,f); fclose(f); if (!n || n==0x1000) return 2;
    unsigned stop=strtoul(argv[2],0,0), budget=strtoul(argv[3],0,0);
    unsigned a=strtoul(argv[4],0,0), p=strtoul(argv[5],0,0);
    mem[0x4000]=strtoul(argv[6],0,0);
    mem[0x3000]=p&0x82; mem[0x3001]=p&0x40;
    mem[0x3104]=2; mem[0x3108]=0x80; mem[0x310c]=0x82;
    m68k_init(); m68k_set_cpu_type(M68K_CPU_TYPE_68020);
    m68k_write_memory_32(0,0xf000); m68k_write_memory_32(4,0x1000); m68k_pulse_reset();
    m68k_set_reg(M68K_REG_SR,0x2700); m68k_set_reg(M68K_REG_D0,a);
    m68k_set_reg(M68K_REG_D4,(p&1)?255:0); m68k_set_reg(M68K_REG_D5,budget);
    m68k_set_reg(M68K_REG_A0,0x4000); m68k_set_reg(M68K_REG_A2,0x3000); m68k_set_reg(M68K_REG_A5,0x3100);
    for (unsigned i=0;i<1000;i++) {
        if (m68k_get_reg(NULL,M68K_REG_PC)==stop) {
            unsigned actual=0x24|(mem[0x3000]&0x82)|(mem[0x3001]&0x40)|((m68k_get_reg(NULL,M68K_REG_D4)&255)?1:0);
            printf("%u %u\n",actual,m68k_get_reg(NULL,M68K_REG_D7)&65535);
            return (m68k_get_reg(NULL,M68K_REG_D7)&65535)==strtoul(argv[7],0,0)?0:4;
        }
        m68k_execute(1);
    }
    return 3;
}
