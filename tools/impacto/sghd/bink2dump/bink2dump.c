/* bink2dump: decode the video of a Bink 2 file with the game's own bink2w32.dll and write raw BGRA frames to stdout
   (for piping into ffmpeg: -f rawvideo -pix_fmt bgra -s WxH -r RATE/DIV -i -).
   usage: bink2dump <bink2w32.dll> <file.bk2> [info]
   "info" prints "width height frames rate div" and exits. Build as a 32-bit program (the DLL is 32-bit). */
#include <windows.h>
#include <stdio.h>
#include <io.h>
#include <fcntl.h>

typedef struct {
  unsigned Width, Height, Frames, FrameNum, LastFrameNum, FrameRate, FrameRateDiv;
} BINKHEAD;  /* first fields of the BINK structure */

typedef void* (__stdcall *PBinkOpen)(const char*, unsigned);
typedef int (__stdcall *PBinkDoFrame)(void*);
typedef void (__stdcall *PBinkNextFrame)(void*);
typedef int (__stdcall *PBinkCopyToBuffer)(void*, void*, int, unsigned, unsigned, unsigned, unsigned);
typedef void (__stdcall *PBinkClose)(void*);
typedef const char* (__stdcall *PBinkGetError)(void);
typedef void (__stdcall *PBinkSetSoundTrack)(unsigned, unsigned*);

#define BINKSURFACE32 3
#define BINKCOPYALL 0x80000000u

int main(int argc, char** argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: bink2dump <bink2w32.dll> <file.bk2> [info]\n");
    return 2;
  }
  HMODULE dll = LoadLibraryA(argv[1]);
  if (!dll) {
    fprintf(stderr, "cannot load %s (%lu)\n", argv[1], GetLastError());
    return 3;
  }
  PBinkOpen open = (PBinkOpen)GetProcAddress(dll, "_BinkOpen@8");
  PBinkDoFrame doFrame = (PBinkDoFrame)GetProcAddress(dll, "_BinkDoFrame@4");
  PBinkNextFrame nextFrame = (PBinkNextFrame)GetProcAddress(dll, "_BinkNextFrame@4");
  PBinkCopyToBuffer copy = (PBinkCopyToBuffer)GetProcAddress(dll, "_BinkCopyToBuffer@28");
  PBinkClose close = (PBinkClose)GetProcAddress(dll, "_BinkClose@4");
  PBinkGetError getError = (PBinkGetError)GetProcAddress(dll, "_BinkGetError@0");
  PBinkSetSoundTrack setTrack = (PBinkSetSoundTrack)GetProcAddress(dll, "_BinkSetSoundTrack@8");
  if (!open || !doFrame || !nextFrame || !copy || !close) {
    fprintf(stderr, "missing exports\n");
    return 3;
  }
  if (setTrack) setTrack(0, NULL); /* video only: the audio is taken from the file by ffmpeg */
  void* bink = open(argv[2], 0);
  if (!bink) {
    fprintf(stderr, "BinkOpen failed: %s\n", getError ? getError() : "?");
    return 4;
  }
  BINKHEAD* h = (BINKHEAD*)bink;
  if (argc > 3) {
    printf("%u %u %u %u %u\n", h->Width, h->Height, h->Frames, h->FrameRate, h->FrameRateDiv);
    close(bink);
    return 0;
  }
  _setmode(_fileno(stdout), _O_BINARY);
  size_t pitch = (size_t)h->Width * 4;
  unsigned char* buf = (unsigned char*)malloc(pitch * h->Height);
  for (unsigned i = 0; i < h->Frames; i++) {
    doFrame(bink);
    copy(bink, buf, (int)pitch, h->Height, 0, 0, BINKSURFACE32 | BINKCOPYALL);
    if (fwrite(buf, 1, pitch * h->Height, stdout) != pitch * h->Height) break;
    if (i + 1 < h->Frames) nextFrame(bink);
  }
  fflush(stdout);
  free(buf);
  close(bink);
  return 0;
}
