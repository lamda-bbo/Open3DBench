def skyline_packing(rects, container_width):
    skyline = [(0, container_width, 0)]  
    placements = [] 

    for (w, h) in rects:
        best_height = float('inf')
        best_pos = None
        best_segment_idx = -1

        for i, (x_s, x_e, s_h) in enumerate(skyline):
            if x_e - x_s >= w:
                current_height = s_h + h
                if (current_height < best_height or 
                    (current_height == best_height and x_s < best_pos[0])):
                    best_height = current_height
                    best_pos = (x_s, s_h)
                    best_segment_idx = i

        if best_pos is None:
            continue

        x_place, y_place = best_pos
        placements.append((x_place, y_place, w, h))
        seg_x_s, seg_x_e, seg_h = skyline[best_segment_idx]

        new_seg = (x_place, x_place + w, seg_h + h)
        remaining_right = (x_place + w, seg_x_e, seg_h) if (x_place + w < seg_x_e) else None

        del skyline[best_segment_idx]
        skyline.insert(best_segment_idx, new_seg)
        if remaining_right:

        if best_segment_idx > 0:
            prev = skyline[best_segment_idx - 1]
            current = skyline[best_segment_idx]
            if prev[1] == current[0] and prev[2] == current[2]:
                merged = (prev[0], current[1], current[2])
                skyline[best_segment_idx - 1: best_segment_idx + 1] = [merged]
                best_segment_idx -= 1

        if best_segment_idx < len(skyline) - 1:
            current = skyline[best_segment_idx]
            next_seg = skyline[best_segment_idx + 1]
            if current[1] == next_seg[0] and current[2] == next_seg[2]:
                merged = (current[0], next_seg[1], current[2])
                skyline[best_segment_idx: best_segment_idx + 2] = [merged]

    return placements, skyline

container_width = 100
rects = [(30, 20), (20, 15), (50, 10)]
placements, skyline = skyline_packing(rects, container_width)

for placement in placements:
    print(placement)