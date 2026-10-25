; Russian plural forms for money amounts in KRONDOR.EXE (v1.02).
;
; Replaces mode 2 of the money formatting function (overlay 130, entry
; 0x0B4A; the branch is at code offset 0x0BCB, file 0x3510B in the original
; EXE): "%ld sovereigns and %ld royal" + "s". The function computed
; sovereigns in [bp-4] and royals in [bp-8] (dwords) and keeps the
; destination buffer (near, DS) in SI.
;
; The overlay jumps here with
;     push cs / push <epilogue> / push ds / push <this code> / retf
; so this code runs with CS = DS = DGROUP, BP = the caller's frame, and
; returns with retf to the epilogue (pop si / leave / retf). DI is kept.
;
; The code is position independent; the strings follow it, each ending
; with 0:
;     joiner (" and "), sovereign forms 1 / 2-4 / 5-20, royal forms 1 / 2-4 / 5-20
;
; Build: nasm -f bin -o money.bin money.asm (the bytes are embedded in
; exe_text.py, see MONEY_CODE).

        bits    16
        cpu     386

start:
        push    di
        call    .base
.base:  pop     bx
        sub     bx, .base - start       ; bx = start (offset in DGROUP)
        mov     ax, ds
        mov     es, ax
        mov     di, si                  ; es:di = destination

        mov     eax, [bp-4]             ; sovereigns
        mov     edx, [bp-8]             ; royals
        test    edx, edx
        jz      .sovereigns             ; no royals: always write sovereigns
        test    eax, eax
        jz      .royals                 ; royals only
.sovereigns:
        push    edx
        mov     cx, 1                   ; sovereign forms start at string 1
        call    write_amount
        pop     edx
        test    edx, edx
        jz      .done
        xor     cx, cx                  ; string 0: joiner
        call    write_string
.royals:
        mov     eax, edx
        mov     cx, 4                   ; royal forms start at string 4
        call    write_amount
.done:
        xor     al, al
        stosb
        pop     di
        retf

; eax = amount, cx = index of its first form; writes "<amount> <form>"
write_amount:
        push    eax
        push    cx
        call    write_number
        mov     al, ' '
        stosb
        pop     cx
        pop     eax
        ; form: 0 (1, 21...), 1 (2-4, 22-24...), 2 (0, 5-20, 25-30...)
        xor     edx, edx
        push    ecx
        mov     ecx, 100
        div     ecx                     ; edx = amount % 100
        pop     ecx
        mov     ax, dx
        cmp     ax, 11
        jb      .units
        cmp     ax, 14
        jbe     .many
.units: push    cx
        mov     cl, 10
        div     cl                      ; ah = (amount % 100) % 10
        pop     cx
        cmp     ah, 1
        je      .one
        cmp     ah, 2
        jb      .many
        cmp     ah, 4
        ja      .many
        inc     cx                      ; 2-4
        jmp     write_string
.many:  add     cx, 2
.one:
        ; fall through
; cx = string index; copies it (without the 0) to es:di
write_string:
        lea     si, [bx + strings - start]
.skip:  jcxz    .copy
.next:  lodsb
        test    al, al
        jnz     .next
        dec     cx
        jmp     .skip
.copy:  lodsb
        test    al, al
        jz      .ret
        stosb
        jmp     .copy
.ret:   ret

; eax = number; writes it in decimal
write_number:
        mov     ecx, 10
        push    word 0xFFFF             ; end mark
.div:   xor     edx, edx
        div     ecx
        add     dl, '0'
        push    dx
        test    eax, eax
        jnz     .div
.out:   pop     ax
        cmp     ax, 0xFFFF
        je      .end
        stosb
        jmp     .out
.end:   ret

strings:
