
int FUN_004c4982(int param_1,undefined4 param_2,undefined4 param_3)

{
  undefined4 uVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  undefined **ppuVar5;
  int iVar6;
  undefined4 unaff_EBX;
  undefined4 unaff_EBP;
  char cVar7;
  undefined4 unaff_ESI;
  undefined4 unaff_EDI;
  bool bVar8;
  bool bVar9;
  undefined4 in_stack_ffffffb0;
  undefined4 *puVar10;
  undefined4 *puVar11;
  undefined4 *puVar12;
  undefined4 *puVar13;
  undefined4 uVar14;
  undefined4 uVar15;
  undefined4 in_stack_ffffffd8;
  undefined **ppuVar16;
  undefined4 in_stack_ffffffe0;
  int iVar17;
  int iVar18;
  undefined4 in_stack_fffffff0;
  undefined4 in_stack_fffffff4;
  undefined4 in_stack_fffffff8;
  
  FUN_004730ad();
  (**(code **)(*(int *)PTR_DAT_005a172c + 0x34))(PTR_DAT_005a172c);
  uVar1 = FUN_00462d74(PTR_PTR_0059ccb8,&PTR_PTR_005b0ee4,0xffffffff);
  iVar2 = FUN_00479191(uVar1);
  uVar1 = FUN_00462d74(PTR_PTR_0059ccb8,&PTR_PTR_005b0f0c,0x76,0x1e,0,2,0xffffffff);
  uVar1 = FUN_004791f7(uVar1);
  uVar15 = 0xf0;
  uVar14 = 0xbe;
  iVar3 = *(int *)(iVar2 + 8) + -1;
  iVar4 = *(int *)(iVar2 + 0xc) + -1;
  puVar10 = &DAT_004f1ed0;
  puVar11 = &DAT_004f1ed0;
  puVar12 = &DAT_004f1ed0;
  puVar13 = &DAT_004f1ed0;
  if (*(int *)(PTR_DAT_005a1334 + 0xc4) == 1) {
    puVar10 = (undefined4 *)FUN_0047943d(0,0,0xf0,600);
    puVar11 = (undefined4 *)FUN_0047943d(0xf0,0,0x140,0xbf);
    puVar12 = (undefined4 *)FUN_0047943d(0xf0,0x198,0x140,0xc0);
    puVar13 = (undefined4 *)FUN_0047943d(0x230,0,0xf0,600);
  }
  iVar17 = 0;
  iVar18 = 0;
  ppuVar16 = &PTR_PTR_004f1c90;
  iVar2 = FUN_00462c22(param_3,&PTR_PTR_005a73f0,unaff_EDI,unaff_ESI,unaff_EBX,in_stack_ffffffb0,
                       iVar3,iVar4,iVar2,puVar10,puVar11,puVar12,puVar13,uVar14,uVar15,
                       in_stack_ffffffd8,&PTR_PTR_004f1c90,in_stack_ffffffe0,0,uVar1,0,
                       in_stack_fffffff0,in_stack_fffffff4,in_stack_fffffff8,unaff_EBP);
  if (iVar2 == 0) {
    iVar2 = 1;
  }
  else {
    iVar2 = 2;
  }
  FUN_00462dc2();
  ppuVar5 = (undefined **)FUN_0048f6d5();
  iVar3 = FUN_00462c22();
  if (iVar3 != 0) {
    FUN_00462dc2();
    ppuVar16 = (undefined **)FUN_0048f6d5();
  }
  iVar3 = FUN_00462c22();
  if (iVar3 == 0) {
    ppuVar5 = &PTR_PTR_004f1c90;
    ppuVar16 = &PTR_PTR_004f1c90;
  }
  FUN_00478ce3();
  FUN_0047908a();
  while( true ) {
    (**(code **)(*(int *)PTR_DAT_005a172c + 0x38))();
    if (*(int *)(PTR_DAT_005a1334 + 0xc4) != 0) {
      FUN_00479410();
      FUN_00479410();
      FUN_00479410();
      FUN_00479410();
    }
    if (*(int *)(PTR_DAT_005a1334 + 0xc4) == 0) {
      FUN_004b68b5();
    }
    FUN_0047898f();
    FUN_0048fe18();
    FUN_0047908a();
    iVar4 = *(int *)(param_1 + 8);
    for (iVar3 = 1; iVar3 <= iVar4; iVar3 = iVar3 + 1) {
      FUN_0048f598();
      iVar6 = FUN_00462c22();
      if (iVar6 == 0) {
        FUN_00478ce3();
      }
      iVar6 = FUN_00462c22();
      if (iVar6 == 0) {
        FUN_00478ce3();
      }
      iVar6 = FUN_00462c22();
      if (iVar6 == 0) {
        FUN_00478ce3();
      }
      iVar6 = FUN_00462c22();
      if (iVar6 == 0) {
        FUN_00462d74();
        FUN_004788d4();
      }
      iVar6 = FUN_00462c22();
      bVar8 = false;
      if (iVar6 != 0) {
        iVar6 = FUN_00462c22();
        bVar8 = iVar6 != 0;
      }
      bVar9 = false;
      if (bVar8) {
        iVar6 = FUN_00462c22();
        bVar9 = iVar6 != 0;
      }
      bVar8 = false;
      if (bVar9) {
        iVar6 = FUN_00462c22();
        bVar8 = iVar6 != 0;
      }
      if (bVar8) {
        FUN_00462d74();
      }
      iVar6 = FUN_00462c22();
      if (iVar6 == 0) {
        FUN_00462d74();
        iVar6 = FUN_004790e6();
        if (iVar6 < 0x10a) {
          FUN_004790e6();
          FUN_004788d4();
          FUN_00462d74();
        }
        else {
          FUN_00462d74();
          FUN_004788d4();
        }
      }
      iVar6 = FUN_00462c22();
      if (iVar6 == 0) {
        FUN_00478ce3();
      }
    }
    FUN_00462d74();
    iVar3 = FUN_004790e6();
    if (iVar3 < 0x10a) {
      FUN_004790e6();
      FUN_004788d4();
      FUN_00462d74();
    }
    else {
      FUN_00462d74();
      FUN_004788d4();
    }
    cVar7 = '\0';
    if (iVar2 == 1) {
      bVar8 = false;
      if (0x155 < *(int *)(PTR_DAT_005a172c + 0xc)) {
        bVar8 = *(int *)(PTR_DAT_005a172c + 0xc) < 0x1cb;
      }
      bVar9 = false;
      if (bVar8) {
        bVar9 = 0x163 < *(int *)(PTR_DAT_005a172c + 0x10);
      }
      cVar7 = '\0';
      if (bVar9) {
        cVar7 = *(int *)(PTR_DAT_005a172c + 0x10) < 0x181;
      }
    }
    else {
      bVar8 = false;
      if (0x115 < *(int *)(PTR_DAT_005a172c + 0xc)) {
        bVar8 = *(int *)(PTR_DAT_005a172c + 0xc) < 0x18b;
      }
      bVar9 = false;
      if (bVar8) {
        bVar9 = 0x163 < *(int *)(PTR_DAT_005a172c + 0x10);
      }
      bVar8 = false;
      if (bVar9) {
        bVar8 = *(int *)(PTR_DAT_005a172c + 0x10) < 0x181;
      }
      if (bVar8) {
        cVar7 = '\x02';
      }
      bVar8 = false;
      if (0x195 < *(int *)(PTR_DAT_005a172c + 0xc)) {
        bVar8 = *(int *)(PTR_DAT_005a172c + 0xc) < 0x20b;
      }
      bVar9 = false;
      if (bVar8) {
        bVar9 = 0x163 < *(int *)(PTR_DAT_005a172c + 0x10);
      }
      bVar8 = false;
      if (bVar9) {
        bVar8 = *(int *)(PTR_DAT_005a172c + 0x10) < 0x181;
      }
      if (bVar8) {
        cVar7 = '\x03';
      }
    }
    iVar3 = FUN_00473067();
    if (iVar3 == 0x1b) break;
    if (iVar3 == 0xd && iVar2 == 1) {
      iVar17 = 1;
      FUN_004730ad();
    }
    if ((ppuVar5[2] != (undefined *)0x0) && (iVar4 = FUN_00462ffb(), iVar3 == iVar4)) {
      iVar17 = 1;
      FUN_004d26b6();
    }
    if ((ppuVar16[2] != (undefined *)0x0) && (iVar4 = FUN_00462ffb(), iVar3 == iVar4)) {
      iVar17 = 2;
      FUN_004d26b6();
    }
    FUN_00478ce3();
    if (*(int *)(PTR_DAT_005a172c + 0x14) == 0) {
      if (iVar2 == 1) {
        FUN_0047898f();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        if (cVar7 == '\x01' && iVar18 == 1) {
          iVar17 = 1;
        }
      }
      else {
        FUN_0047898f();
        FUN_0047898f();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        if (cVar7 == '\x02' && iVar18 == 1) {
          iVar17 = 1;
        }
        if (cVar7 == '\x03' && iVar18 == 1) {
          iVar17 = 2;
        }
      }
      iVar18 = 0;
    }
    else if (iVar2 == 1) {
      if (cVar7 == '\x01') {
        FUN_0047898f();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        if (iVar18 == 0) {
          FUN_004d26b6();
        }
        iVar18 = 1;
      }
      else {
        FUN_0047898f();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
      }
    }
    else {
      if (cVar7 == '\0') {
        FUN_0047898f();
        FUN_0047898f();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
      }
      if (cVar7 == '\x02') {
        FUN_0047898f();
        FUN_0047898f();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        if (iVar18 == 0) {
          FUN_004d26b6();
        }
        iVar18 = 1;
      }
      if (cVar7 == '\x03') {
        FUN_0047898f();
        FUN_0047898f();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        FUN_004790e6();
        FUN_004788d4();
        FUN_00479177();
        FUN_004790e6();
        FUN_00462dc2();
        FUN_004790e6();
        FUN_00479177();
        FUN_004790e6();
        FUN_004786fe();
        if (iVar18 == 0) {
          FUN_004d26b6();
        }
        iVar18 = 1;
      }
    }
    FUN_0047898f();
    (**(code **)(*(int *)PTR_DAT_005a1334 + 0x38))();
    if (iVar17 != 0) {
      if (*(int *)(PTR_DAT_005a1334 + 0xc4) == 0) {
        FUN_004b68b5();
      }
      else {
        FUN_00479410();
        FUN_00479410();
        FUN_00479410();
        FUN_00479410();
      }
      return iVar17;
    }
  }
  return 0;
}

