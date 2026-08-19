"""创建中文字体子集 + 注入 EXE 新节"""
import os
import sys
import struct
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter

def create_subset_font(source_font, chars_file, output_path, font_number=None):
    """从系统字体创建子集"""
    chars = []
    with open(chars_file, 'r', encoding='utf-8') as f:
        text = f.read()
        chars = list(text)
    
    ascii_chars = [chr(i) for i in range(32, 127)]
    all_chars = ''.join(set(ascii_chars + chars))
    
    print(f"Creating subset font with {len(all_chars)} characters...")
    
    # Load font
    if font_number is not None:
        font = TTFont(source_font, fontNumber=font_number)
    else:
        font = TTFont(source_font)
    
    # Create subsetter
    subsetter = Subsetter()
    subsetter.populate(text=all_chars)
    subsetter.subset(font)
    
    # Save
    font.save(output_path)
    font.close()
    
    size = os.path.getsize(output_path)
    print(f"Subset font saved: {output_path}")
    print(f"Size: {size} bytes ({size/1024:.1f} KB)")
    return size

def add_pe_section(exe_path, section_name, data):
    """在 EXE 末尾添加新节"""
    with open(exe_path, 'rb') as f:
        exe_data = bytearray(f.read())
    
    # Parse PE header
    pe_off = struct.unpack('<I', exe_data[0x3C:0x40])[0]
    coff = pe_off + 4
    
    # Read some fields
    num_sections = struct.unpack('<H', exe_data[coff+2:coff+4])[0]
    
    # PE magic
    pe_magic = struct.unpack('<H', exe_data[coff+20:coff+22])[0]
    
    # Optional header size
    if pe_magic == 0x10b:  # PE32
        opt_header_size = 224
        file_alignment_offset = coff + 20 + 36
        section_alignment_offset = coff + 20 + 32
        size_of_image_offset = coff + 20 + 56
    else:
        opt_header_size = 240
        file_alignment_offset = coff + 20 + 48
        section_alignment_offset = coff + 20 + 40
        size_of_image_offset = coff + 20 + 64
    
    section_table_offset = pe_off + 4 + 20 + opt_header_size
    
    # Get section alignment and file alignment
    file_align = struct.unpack('<I', exe_data[file_alignment_offset:file_alignment_offset+4])[0]
    sect_align = struct.unpack('<I', exe_data[section_alignment_offset:section_alignment_offset+4])[0]
    
    # Get last section info for new section placement
    last_sec_offset = section_table_offset + (num_sections - 1) * 40
    last_sec = exe_data[last_sec_offset:last_sec_offset+40]
    last_vrva = struct.unpack('<I', last_sec[12:16])[0]
    last_vsize = struct.unpack('<I', last_sec[8:12])[0]
    last_rsize = struct.unpack('<I', last_sec[16:20])[0]
    last_roff = struct.unpack('<I', last_sec[20:24])[0]
    
    # Calculate new section's virtual address (aligned)
    new_vrva = last_vrva + ((last_vsize + sect_align - 1) // sect_align) * sect_align
    
    # Pad data to file alignment
    padded_size = ((len(data) + file_align - 1) // file_align) * file_align
    padded_data = data + b'\x00' * (padded_size - len(data))
    
    # New section raw offset = end of file
    new_roff = len(exe_data)
    new_vsize = ((len(data) + sect_align - 1) // sect_align) * sect_align
    new_rsize = padded_size
    
    # Create new section header
    new_sec = bytearray(40)
    # Name (8 bytes)
    name_bytes = section_name.encode('ascii')[:8]
    new_sec[0:len(name_bytes)] = name_bytes
    # VirtualSize
    struct.pack_into('<I', new_sec, 8, new_vsize)
    # VirtualAddress
    struct.pack_into('<I', new_sec, 12, new_vrva)
    # SizeOfRawData
    struct.pack_into('<I', new_sec, 16, new_rsize)
    # PointerToRawData
    struct.pack_into('<I', new_sec, 20, new_roff)
    # Characteristics (0xC0000040 = readable, writable, initialized data)
    struct.pack_into('<I', new_sec, 36, 0xC0000040)
    
    # Append data
    exe_data.extend(padded_data)
    
    # Update section count
    struct.pack_into('<H', exe_data, coff+2, num_sections + 1)
    
    # Update SizeOfImage
    old_image_size = struct.unpack('<I', exe_data[size_of_image_offset:size_of_image_offset+4])[0]
    new_image_size = new_vrva + new_vsize
    struct.pack_into('<I', exe_data, size_of_image_offset, new_image_size)
    
    # Write new section header (append after last section in section table)
    exe_data.extend(new_sec)
    
    with open(exe_path, 'wb') as f:
        f.write(exe_data)
    
    print(f"\nNew section '{section_name}':")
    print(f"  VA: 0x{new_vrva + 0x400000:X} (file offset: 0x{new_roff:X})")
    print(f"  VirtualSize: {new_vsize}, RawSize: {new_rsize}")
    print(f"  Old SizeOfImage: 0x{old_image_size:X}, New: 0x{new_image_size:X}")
    
    return new_vrva + 0x400000  # Return VA

def patch_font_references(exe_path, font_offsets, new_va):
    """修改EXE中字体数据指针指向新节"""
    with open(exe_path, 'rb') as f:
        exe_data = bytearray(f.read())
    
    patched = 0
    for old_file_offset, font_name in font_offsets:
        # Find all references to the old font address in code
        old_va = old_file_offset + 0x400000  # approximate
        
        # Search for push/mov instructions referencing this address
        old_bytes = struct.pack('<I', old_va)
        new_bytes = struct.pack('<I', new_va)
        
        # Simple search in code section (0x1000 to 0xE0000)
        code_start = 0x1000
        code_end = 0xE0000
        
        idx = 0
        while idx < code_end:
            pos = exe_data.find(old_bytes, idx, code_end)
            if pos == -1:
                break
            
            # Check if this is likely a code reference (not random data match)
            # Look at the bytes before the address for common patterns
            # push = 0x68, mov = 0xB8-0xBF or 0xC7
            if pos >= 1:
                prev_byte = exe_data[pos-1]
                if prev_byte in [0x68, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF]:
                    exe_data[pos:pos+4] = new_bytes
                    patched += 1
                    print(f"  Patched reference at file offset 0x{pos:X} ({font_name})")
            
            idx = pos + 4
    
    with open(exe_path, 'wb') as f:
        f.write(exe_data)
    
    print(f"Total references patched: {patched}")
    return patched

def main():
    exe_path = r'd:\StaticHanHua\Projects\EschalonBook\Game\eschalon_book_1.exe'
    chars_file = r'd:\StaticHanHua\Projects\EschalonBook\chinese_chars.txt'
    output_font = r'd:\StaticHanHua\Projects\EschalonBook\fonts\cn_subset.ttf'
    source_font = r'C:\Windows\Fonts\simhei.ttf'
    
    # Make backup
    import shutil
    bak_path = exe_path + '.bak2'
    if not os.path.exists(bak_path):
        shutil.copy2(exe_path, bak_path)
        print(f"Backup: {bak_path}")
    
    # Step 1: Create subset font
    print("=" * 60)
    print("Step 1: Creating Chinese font subset...")
    
    # Try different fonts
    fonts_to_try = [
        (r'C:\Windows\Fonts\simhei.ttf', None),
        (r'C:\Windows\Fonts\simkai.ttf', None),
        (r'C:\Windows\Fonts\simsun.ttc', 0),
        (r'C:\Windows\Fonts\msyh.ttc', 0),
    ]
    
    source_font = None
    font_number = None
    for f, n in fonts_to_try:
        if os.path.exists(f):
            source_font = f
            font_number = n
            print(f"Using: {source_font}" + (f" (font #{n})" if n is not None else ""))
            break
    
    if not source_font:
        print("No Chinese font found! Install a Chinese font first.")
        return
    
    try:
        size = create_subset_font(source_font, chars_file, output_font, font_number)
    except Exception as e:
        print(f"ERROR creating subset font: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Add new section to EXE
    print("\n" + "=" * 60)
    print("Step 2: Adding font section to EXE...")
    
    with open(output_font, 'rb') as f:
        font_data = f.read()
    
    new_va = add_pe_section(exe_path, '.cnfont', font_data)
    
    # Step 3: The font data pointer needs to be updated
    # For now, we note the VA and the user needs to manually update the pointer in IDA
    print(f"\n" + "=" * 60)
    print("Step 3: Font pointer update needed")
    print(f"Chinese font is now at VA 0x{new_va:X} in the new '.cnfont' section")
    print(f"The original font data at VA 0x4E1A2F (DS_Celtic) needs its pointer redirected.")
    print(f"\nIn IDA, find all references to the old font data and update to 0x{new_va:X}")

if __name__ == '__main__':
    main()
