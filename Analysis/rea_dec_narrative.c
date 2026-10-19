
/* WARNING: Removing unreachable block (ram,0x004c69f4) */
/* WARNING: Removing unreachable block (ram,0x004c69fa) */
/* WARNING: Removing unreachable block (ram,0x004c6a12) */
/* WARNING: Removing unreachable block (ram,0x004c6a18) */
/* WARNING: Removing unreachable block (ram,0x004c6a30) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_004c69ad(int param_1,int param_2,uint param_3)

{
  int *piVar1;
  bool bVar2;
  int iVar3;
  int iVar4;
  undefined4 uVar5;
  uint uVar6;
  int iVar7;
  undefined4 uVar8;
  int iVar9;
  int iVar10;
  int iVar11;
  int iVar12;
  undefined4 unaff_EBX;
  int iVar13;
  undefined4 unaff_EBP;
  undefined4 unaff_ESI;
  undefined **ppuVar14;
  undefined4 unaff_EDI;
  undefined4 *puVar15;
  int iVar16;
  bool bVar17;
  undefined4 in_stack_ffffffa8;
  undefined4 in_stack_ffffffac;
  undefined **ppuVar18;
  undefined4 in_stack_ffffffb4;
  undefined4 in_stack_ffffffb8;
  undefined4 in_stack_ffffffbc;
  undefined4 in_stack_ffffffc0;
  int iVar19;
  undefined4 in_stack_ffffffc4;
  int iVar20;
  undefined4 in_stack_ffffffc8;
  undefined4 in_stack_ffffffcc;
  int iVar21;
  undefined4 in_stack_ffffffd0;
  undefined4 in_stack_ffffffd4;
  int iVar22;
  undefined4 in_stack_ffffffdc;
  undefined4 in_stack_ffffffe0;
  int iVar23;
  undefined4 in_stack_ffffffe8;
  undefined *puVar24;
  undefined4 in_stack_ffffffec;
  int iVar25;
  undefined4 in_stack_fffffff0;
  float fVar26;
  undefined **ppuVar27;
  undefined **ppuVar28;
  
  iVar3 = 0;
  if (param_2 == 0) {
    iVar3 = *(int *)(*(int *)(PTR_DAT_005a1334 + 0xfc) + 0x18 + param_1 * 4);
  }
  if (iVar3 == 0) {
    puVar15 = &DAT_004f1ed0;
    if (param_2 == 0) {
      uVar5 = FUN_004721af(&PTR_PTR_005b16b4);
      puVar15 = (undefined4 *)FUN_00485970(uVar5);
    }
    if (param_2 == 1) {
      uVar5 = FUN_004721af(&PTR_PTR_005b16f8);
      puVar15 = (undefined4 *)FUN_00485970(uVar5);
    }
    ppuVar18 = &PTR_PTR_004f1c90;
    while (iVar3 = FUN_0046f14f(puVar15), iVar3 == 0) {
      uVar5 = FUN_0046f385(puVar15);
      ppuVar27 = (undefined **)FUN_0046f385(puVar15);
      iVar3 = FUN_00463061(uVar5);
      if (iVar3 == param_1) {
        ppuVar18 = ppuVar27;
      }
    }
    FUN_004721e1(puVar15);
    iVar4 = FUN_0048f6a3(ppuVar18,&PTR_PTR_005b1734,*(undefined4 *)(PTR_DAT_005a13ac + 0xc));
    ppuVar27 = &PTR_PTR_004f1c90;
    ppuVar18 = &PTR_PTR_004f1c90;
    bVar17 = false;
    iVar23 = *(int *)(iVar4 + 8);
    for (iVar3 = 1; iVar3 <= iVar23; iVar3 = iVar3 + 1) {
      bVar2 = false;
      uVar5 = FUN_0048f598(iVar4,iVar3,1);
      iVar7 = FUN_00462c22(uVar5,&PTR_PTR_005a2440,unaff_EDI,unaff_ESI,unaff_EBX,in_stack_ffffffa8,
                           in_stack_ffffffac,ppuVar18,in_stack_ffffffb4,in_stack_ffffffb8,
                           in_stack_ffffffbc,in_stack_ffffffc0,in_stack_ffffffc4,in_stack_ffffffc8,
                           in_stack_ffffffcc,in_stack_ffffffd0,in_stack_ffffffd4,iVar4,
                           in_stack_ffffffdc,in_stack_ffffffe0,iVar23,in_stack_ffffffe8,
                           in_stack_ffffffec,in_stack_fffffff0,ppuVar27,iVar3,unaff_EBP);
      if (iVar7 == 0) {
        bVar2 = true;
        if (bVar17) {
          bVar17 = false;
        }
        else {
          bVar17 = true;
        }
      }
      if (bVar17) {
        if (!bVar2) {
          ppuVar18 = (undefined **)FUN_00462d74();
        }
      }
      else if (!bVar2) {
        ppuVar27 = (undefined **)FUN_00462d74();
      }
    }
    puVar15 = &DAT_004f1ed0;
    ppuVar28 = ppuVar27;
    if (param_3 == 1) {
      uVar5 = FUN_00462d74(PTR_PTR_0059ccb8,&PTR_PTR_005b0f78,0xffffffff);
      puVar15 = (undefined4 *)FUN_00479191(uVar5);
    }
    if (param_3 == 2) {
      uVar5 = FUN_00462d74(PTR_PTR_0059ccb8,&PTR_PTR_005b1744,0xffffffff);
      puVar15 = (undefined4 *)FUN_00479191(uVar5);
    }
    if ((param_3 == 0) && (600 < (int)ppuVar27[2])) {
      uVar5 = FUN_00462d74(PTR_PTR_0059ccb8,&PTR_PTR_005b1744,0xffffffff);
      puVar15 = (undefined4 *)FUN_00479191(uVar5);
    }
    uVar5 = FUN_00462d74(PTR_PTR_0059ccb8,&PTR_PTR_005b0f0c,0x76,0x1e,0,2,0xffffffff);
    uVar5 = FUN_004791f7(uVar5);
    if (param_2 == 0) {
      FUN_004d26b6(&PTR_PTR_005b1778);
    }
    uVar6 = (uint)(600 < (int)ppuVar27[2]);
    if (600 < (int)ppuVar27[2] == 0) {
      uVar6 = param_3;
    }
    if (uVar6 == 0) {
      (*(code *)PTR_FUN_0059ad38)(4,0,0,0);
      FUN_004bdeb8(ppuVar27,5);
    }
    else {
      ppuVar14 = &PTR_PTR_004f1c90;
      iVar7 = FUN_00463930(u_SFX_Narration__005b1784 + 0xd,200);
      iVar4 = 1;
      puVar24 = ppuVar27[2];
      for (iVar16 = 1; iVar16 <= (int)puVar24; iVar16 = iVar16 + 1) {
        uVar8 = FUN_0048f598(ppuVar27,iVar16,1);
        iVar25 = FUN_00462c22(uVar8,&PTR_PTR_005a8e34,unaff_EDI,unaff_ESI,unaff_EBX,
                              in_stack_ffffffa8,puVar15,ppuVar18,in_stack_ffffffb4,in_stack_ffffffb8
                              ,uVar5,in_stack_ffffffc0,in_stack_ffffffc4,in_stack_ffffffc8,
                              in_stack_ffffffcc,iVar4,in_stack_ffffffd4,ppuVar27,in_stack_ffffffdc,
                              iVar7,iVar23,puVar24,in_stack_ffffffec,in_stack_fffffff0,ppuVar28,
                              iVar3,unaff_EBP);
        if (iVar25 == 0) {
          iVar4 = iVar4 + 2;
          ppuVar14 = &PTR_PTR_0059cc14;
        }
        else {
          ppuVar14 = (undefined **)FUN_00462d74();
          iVar25 = FUN_00462c22(uVar8,&PTR_PTR_005a6fd4);
          if (iVar25 == 0) {
            uVar8 = FUN_00462d74(*(undefined4 *)(iVar7 + 0x18 + iVar4 * 4),ppuVar14);
            iVar25 = FUN_004790e6(uVar8);
            if (iVar25 < 0x14f) {
              iVar9 = FUN_00462d74(*(undefined4 *)(iVar7 + 0x18 + iVar4 * 4),ppuVar14);
              *(int *)(iVar9 + 4) = *(int *)(iVar9 + 4) + 1;
              iVar25 = *(int *)(iVar7 + 0x18 + iVar4 * 4);
              piVar1 = (int *)(iVar25 + 4);
              *piVar1 = *piVar1 + -1;
              if (*piVar1 == 0) {
                FUN_004653ae(iVar25);
              }
              *(int *)(iVar7 + 0x18 + iVar4 * 4) = iVar9;
              ppuVar14 = &PTR_PTR_0059cc14;
            }
            else {
              iVar4 = iVar4 + 1;
              ppuVar14[1] = ppuVar14[1] + 1;
              iVar25 = *(int *)(iVar7 + 0x18 + iVar4 * 4);
              piVar1 = (int *)(iVar25 + 4);
              *piVar1 = *piVar1 + -1;
              if (*piVar1 == 0) {
                FUN_004653ae(iVar25);
              }
              *(undefined ***)(iVar7 + 0x18 + iVar4 * 4) = ppuVar14;
              ppuVar14 = &PTR_PTR_0059cc14;
            }
          }
        }
      }
      uVar8 = FUN_00462d74(*(undefined4 *)(iVar7 + 0x18 + iVar4 * 4),ppuVar14);
      iVar16 = FUN_004790e6(uVar8);
      if (iVar16 < 0x150) {
        iVar25 = FUN_00462d74(*(undefined4 *)(iVar7 + 0x18 + iVar4 * 4),ppuVar14);
        *(int *)(iVar25 + 4) = *(int *)(iVar25 + 4) + 1;
        iVar16 = *(int *)(iVar7 + 0x18 + iVar4 * 4);
        piVar1 = (int *)(iVar16 + 4);
        *piVar1 = *piVar1 + -1;
        if (*piVar1 == 0) {
          FUN_004653ae(iVar16);
        }
        *(int *)(iVar7 + 0x18 + iVar4 * 4) = iVar25;
      }
      else {
        iVar4 = iVar4 + 1;
        ppuVar14[1] = ppuVar14[1] + 1;
        iVar16 = *(int *)(iVar7 + 0x18 + iVar4 * 4);
        piVar1 = (int *)(iVar16 + 4);
        *piVar1 = *piVar1 + -1;
        if (*piVar1 == 0) {
          FUN_004653ae(iVar16);
        }
        *(undefined ***)(iVar7 + 0x18 + iVar4 * 4) = ppuVar14;
      }
      iVar21 = 0;
      iVar25 = 0;
      iVar20 = 0xd4;
      iVar19 = 0x32;
      iVar9 = puVar15[2] + -1;
      iVar10 = puVar15[3] + -1;
      iVar16 = iVar4 / 0x15;
      fVar26 = (float)u_SFX_Narration__005b1784._28_4_;
      if (iVar4 % 0x15 != 0) {
        iVar16 = iVar16 + 1;
      }
      do {
        (**(code **)(*(int *)PTR_DAT_005a172c + 0x38))(PTR_DAT_005a172c);
        iVar22 = 0;
        if (fVar26 < 1.0) {
          fVar26 = fVar26 + _DAT_005b17a4;
        }
        FUN_004b68b5();
        (**(code **)(*(int *)PTR_DAT_005a1334 + 0x44))(PTR_DAT_005a1334);
        FUN_00478d9c(fVar26);
        FUN_00478ce3(0xff,0xff,0xff);
        FUN_0047898f(puVar15,(float)iVar20,(float)iVar19,0);
        if (param_3 == 2) {
          FUN_0048fe18(iVar20,iVar19,iVar9,iVar10);
        }
        FUN_0047908a(PTR_DAT_0059cd0c);
        FUN_00478ce3(5,5,5);
        for (iVar13 = 1; iVar13 < 0x16; iVar13 = iVar13 + 1) {
          FUN_004788d4(*(undefined4 *)(iVar7 + 0x18 + (iVar13 + iVar25) * 4),0x436b0000,
                       (float)(iVar13 * 0xf + 0x41));
        }
        if (iVar25 + 0x16 < iVar4) {
          ppuVar14 = &PTR_PTR_005b17a8;
        }
        else {
          ppuVar14 = &PTR_PTR_005ac274;
        }
        bVar17 = false;
        if (0x155 < *(int *)(PTR_DAT_005a172c + 0xc)) {
          bVar17 = *(int *)(PTR_DAT_005a172c + 0xc) < 0x1cb;
        }
        bVar2 = false;
        if (bVar17) {
          bVar2 = 0x19f < *(int *)(PTR_DAT_005a172c + 0x10);
        }
        bVar17 = false;
        if (bVar2) {
          bVar17 = *(int *)(PTR_DAT_005a172c + 0x10) < 0x1bd;
        }
        FUN_00478ce3(0xff,0xff,0xff);
        iVar13 = FUN_00473067();
        if (*(int *)(PTR_DAT_005a172c + 0x14) == 0) {
          FUN_0047898f(uVar5,0x43aa8000,0x43d20000,0);
          FUN_00478ce3(5,5,5);
          iVar11 = FUN_004790e6(ppuVar14,0x43d58000);
          FUN_004788d4(ppuVar14,(float)(399 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)));
          iVar11 = FUN_00479177(ppuVar14,1);
          iVar11 = FUN_004790e6(ppuVar14,(float)(iVar11 + 0x1aa));
          uVar8 = FUN_00462dc2(ppuVar14,0,1);
          iVar12 = FUN_004790e6(uVar8);
          iVar11 = FUN_00479177(ppuVar14,(float)((399 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)
                                                 ) + iVar12));
          iVar11 = FUN_004790e6(ppuVar14,(float)(iVar11 + 0x1aa));
          FUN_004786fe((float)(399 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)));
          if (bVar17 && iVar21 == 1) {
            iVar21 = FUN_00462c22(ppuVar14,&PTR_PTR_005b17a8);
            if (iVar21 == 0) {
              iVar22 = 1;
            }
            else {
              iVar22 = 2;
            }
          }
          iVar21 = 0;
        }
        else if (bVar17) {
          FUN_0047898f(uVar5,0x43aa8000,0x43d20000,1);
          FUN_00478ce3(5,5,5);
          iVar11 = FUN_004790e6(ppuVar14,0x43d60000);
          FUN_004788d4(ppuVar14,(float)(400 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)));
          iVar11 = FUN_00479177(ppuVar14,1);
          iVar11 = FUN_004790e6(ppuVar14,(float)(iVar11 + 0x1ab));
          uVar8 = FUN_00462dc2(ppuVar14,0,1);
          iVar12 = FUN_004790e6(uVar8);
          iVar11 = FUN_00479177(ppuVar14,(float)((400 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)
                                                 ) + iVar12));
          iVar11 = FUN_004790e6(ppuVar14,(float)(iVar11 + 0x1ab));
          FUN_004786fe((float)(400 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)));
          if (iVar21 == 0) {
            FUN_004d26b6(&PTR_PTR_005b0f50);
          }
          iVar21 = 1;
        }
        else {
          FUN_0047898f(uVar5,0x43aa8000,0x43d20000,0);
          FUN_00478ce3(5,5,5);
          iVar11 = FUN_004790e6(ppuVar14,0x43d58000);
          FUN_004788d4(ppuVar14,(float)(399 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)));
          iVar11 = FUN_00479177(ppuVar14,1);
          iVar11 = FUN_004790e6(ppuVar14,(float)(iVar11 + 0x1aa));
          uVar8 = FUN_00462dc2(ppuVar14,0,1);
          iVar12 = FUN_004790e6(uVar8);
          iVar11 = FUN_00479177(ppuVar14,(float)((399 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)
                                                 ) + iVar12));
          iVar11 = FUN_004790e6(ppuVar14,(float)(iVar11 + 0x1aa));
          FUN_004786fe((float)(399 - ((int)(iVar11 + (iVar11 >> 0x1f & 1U)) >> 1)));
        }
        if (1 < iVar16) {
                    /* WARNING: Subroutine does not return */
          __break(iVar16,0x43660000,0x43d58000);
        }
        FUN_00478ce3(0xff,0xff,0xff);
        iVar11 = *(int *)(PTR_DAT_005a172c + 0xc);
        FUN_0047898f(*(undefined4 *)(*(int *)(PTR_DAT_005a172c + 0x40) + 0x3c),(float)iVar11,
                     (float)*(int *)(PTR_DAT_005a172c + 0x10),0);
        bVar17 = iVar13 == 0xd || iVar13 == 0x6d;
        if (iVar13 != 0xd && iVar13 != 0x6d) {
          bVar17 = iVar13 == 0x6f;
        }
        if (bVar17) {
          iVar22 = FUN_00462c22(ppuVar14,&PTR_PTR_005b17a8,unaff_EDI,unaff_ESI,unaff_EBX,iVar11,
                                puVar15,ppuVar18,iVar9,iVar10,uVar5,iVar19,iVar20,iVar16,iVar21,
                                iVar4,iVar22,ppuVar27,iVar13,iVar7,iVar23,puVar24,iVar25,fVar26,
                                ppuVar28,iVar3,unaff_EBP);
          if (iVar22 == 0) {
            iVar22 = 1;
          }
          else {
            iVar22 = 2;
          }
          FUN_004730ad();
        }
        if (iVar22 == 1) {
          iVar25 = iVar25 + 0x15;
        }
        (**(code **)(*(int *)PTR_DAT_005a1334 + 0x38))(PTR_DAT_005a1334);
      } while (iVar22 != 2);
    }
    if (param_2 == 0) {
      *(undefined4 *)(*(int *)(PTR_DAT_005a1334 + 0xfc) + 0x18 + param_1 * 4) = 1;
    }
    if (ppuVar18[2] != (undefined *)0x0) {
      FUN_004c7c26(ppuVar18,0,0,1);
    }
    FUN_004b68b5();
  }
  return 0;
}

