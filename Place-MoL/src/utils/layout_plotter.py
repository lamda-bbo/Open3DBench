"""
Layout plotting utilities for macro placement visualization.
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from typing import Optional, List


class LayoutPlotter:
    """
    Utility class for plotting macro placement layouts.
    """
    
    @staticmethod
    def plot_macros(macro_x: np.ndarray,
                    macro_y: np.ndarray,
                    macro_w: np.ndarray,
                    macro_h: np.ndarray,
                    xl: float,
                    yl: float,
                    xh: float,
                    yh: float,
                    iteration: Optional[int] = None,
                    hpwl_val: Optional[float] = None,
                    title: Optional[str] = None,
                    figure_path: Optional[str] = None,
                    figsize: tuple = (12, 12),
                    dpi: int = 150,
                    edgecolor: str = 'blue',
                    facecolor: str = 'lightblue',
                    alpha: float = 0.7,
                    show_grid: bool = True) -> str:
        """
        Plot macro placement layout.
        
        Args:
            macro_x: Array of macro x coordinates
            macro_y: Array of macro y coordinates
            macro_w: Array of macro widths
            macro_h: Array of macro heights
            xl: Layout left boundary
            yl: Layout bottom boundary
            xh: Layout right boundary
            yh: Layout top boundary
            iteration: Current iteration number (optional, for title)
            hpwl_val: Current HPWL value (optional, for title)
            title: Custom title (optional, overrides auto-generated title)
            figure_path: Path to save the figure (required)
            figsize: Figure size (width, height) in inches
            dpi: DPI for saved figure
            edgecolor: Edge color for macro rectangles
            facecolor: Face color for macro rectangles
            alpha: Transparency for macro rectangles
            show_grid: Whether to show grid
        
        Returns:
            figure_path: Path where the figure was saved
        """
        if figure_path is None:
            raise ValueError("figure_path must be provided")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(figure_path) if os.path.dirname(figure_path) else '.', exist_ok=True)
        
        # Create figure and axis
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        
        # Set axis limits to layout boundaries
        ax.set_xlim(xl, xh)
        ax.set_ylim(yl, yh)
        
        # Set aspect ratio to be equal
        ax.set_aspect('equal')
        
        # Draw each macro as a rectangle
        n_macros = len(macro_x)
        for i in range(n_macros):
            rect = Rectangle(
                (macro_x[i], macro_y[i]),
                macro_w[i],
                macro_h[i],
                linewidth=1,
                edgecolor=edgecolor,
                facecolor=facecolor,
                alpha=alpha
            )
            ax.add_patch(rect)
        
        # Set labels and title
        ax.set_xlabel('X (microns)', fontsize=12)
        ax.set_ylabel('Y (microns)', fontsize=12)
        
        if title is None:
            if iteration is not None and hpwl_val is not None:
                title = f'Macro Placement - Iteration {iteration}, HPWL: {hpwl_val:.2f}'
            elif iteration is not None:
                title = f'Macro Placement - Iteration {iteration}'
            elif hpwl_val is not None:
                title = f'Macro Placement - HPWL: {hpwl_val:.2f}'
            else:
                title = 'Macro Placement'
        
        ax.set_title(title, fontsize=14)
        
        # Add grid for better visibility
        if show_grid:
            ax.grid(True, linestyle='--', alpha=0.3)
        
        # Save figure
        plt.tight_layout()
        plt.savefig(figure_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        
        return figure_path
    
    @staticmethod
    def plot_3d_macro_placement(
            bottom_die_macro_x: np.ndarray,
            bottom_die_macro_y: np.ndarray,
            bottom_die_macro_w: np.ndarray,
            bottom_die_macro_h: np.ndarray,
            upper_die_macro_x: np.ndarray,
            upper_die_macro_y: np.ndarray,
            upper_die_macro_w: np.ndarray,
            upper_die_macro_h: np.ndarray,
            xl: float,
            yl: float,
            xh: float,
            yh: float,
            figure_path: str,
            dpi: int = 150,
            highlight_bottom_idx: Optional[int] = None,
            highlight_upper_idx: Optional[int] = None) -> str:
        """
        Plot 3D macro placement with two subplots:
        - Left: Bottom die macros
        - Right: Upper die macros
        
        Args:
            bottom_die_macro_x: Array of bottom die macro x coordinates
            bottom_die_macro_y: Array of bottom die macro y coordinates
            bottom_die_macro_w: Array of bottom die macro widths
            bottom_die_macro_h: Array of bottom die macro heights
            upper_die_macro_x: Array of upper die macro x coordinates
            upper_die_macro_y: Array of upper die macro y coordinates
            upper_die_macro_w: Array of upper die macro widths
            upper_die_macro_h: Array of upper die macro heights
            xl: Layout left boundary
            yl: Layout bottom boundary
            xh: Layout right boundary
            yh: Layout top boundary
            figure_path: Path to save the figure (required)
            dpi: DPI for saved figure
            highlight_bottom_idx: Optional index of bottom die macro to highlight
            highlight_upper_idx: Optional index of upper die macro to highlight
        
        Returns:
            figure_path: Path where the figure was saved
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(figure_path) if os.path.dirname(figure_path) else '.', exist_ok=True)
        
        # Create figure with 2 subplots
        fig, axes = plt.subplots(1, 2, figsize=(24, 12))
        
        # Plot 1: Bottom Die Macros (left subplot)
        ax1 = axes[0]
        ax1.set_xlim(xl, xh)
        ax1.set_ylim(yl, yh)
        ax1.set_aspect('equal')
        
        # Draw bottom die macros (green rectangles)
        n_bottom = len(bottom_die_macro_x)
        for i in range(n_bottom):
            x, y = float(bottom_die_macro_x[i]), float(bottom_die_macro_y[i])
            w, h = float(bottom_die_macro_w[i]), float(bottom_die_macro_h[i])
            # Skip invalid rectangles
            if w <= 0 or h <= 0 or not np.isfinite([x, y, w, h]).all():
                continue
            is_highlighted = (highlight_bottom_idx is not None and i == highlight_bottom_idx)
            rect = Rectangle(
                (x, y), w, h,
                linewidth=3 if is_highlighted else 1,
                edgecolor='darkgreen' if is_highlighted else 'green',
                facecolor='yellow' if is_highlighted else 'lightgreen',
                alpha=0.9 if is_highlighted else 0.7
            )
            ax1.add_patch(rect)
        
        ax1.set_xlabel('X (microns)', fontsize=16)
        ax1.set_ylabel('Y (microns)', fontsize=16)
        title = f'Bottom Die Macros ({n_bottom} macros)'
        if highlight_bottom_idx is not None:
            title += f' [Highlighted: macro {highlight_bottom_idx}]'
        ax1.set_title(title, fontsize=18)
        ax1.grid(True, linestyle='--', alpha=0.3)
        # Increase tick label font size
        ax1.tick_params(labelsize=16)
        
        # Plot 2: Upper Die Macros (right subplot)
        ax2 = axes[1]
        ax2.set_xlim(xl, xh)
        ax2.set_ylim(yl, yh)
        ax2.set_aspect('equal')
        
        # Draw upper die macros (red rectangles)
        n_upper = len(upper_die_macro_x)
        for i in range(n_upper):
            x, y = float(upper_die_macro_x[i]), float(upper_die_macro_y[i])
            w, h = float(upper_die_macro_w[i]), float(upper_die_macro_h[i])
            # Skip invalid rectangles
            if w <= 0 or h <= 0 or not np.isfinite([x, y, w, h]).all():
                continue
            is_highlighted = (highlight_upper_idx is not None and i == highlight_upper_idx)
            rect = Rectangle(
                (x, y), w, h,
                linewidth=3 if is_highlighted else 1,
                edgecolor='darkred' if is_highlighted else 'red',
                facecolor='yellow' if is_highlighted else 'lightcoral',
                alpha=0.9 if is_highlighted else 0.7
            )
            ax2.add_patch(rect)
        
        ax2.set_xlabel('X (microns)', fontsize=16)
        ax2.set_ylabel('Y (microns)', fontsize=16)
        title = f'Upper Die Macros ({n_upper} macros)'
        if highlight_upper_idx is not None:
            title += f' [Highlighted: macro {highlight_upper_idx}]'
        ax2.set_title(title, fontsize=18)
        ax2.grid(True, linestyle='--', alpha=0.3)
        # Increase tick label font size
        ax2.tick_params(labelsize=16)
        
        # Save figure
        plt.tight_layout()
        plt.savefig(figure_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        
        return figure_path
    
    @staticmethod
    def plot_3d_macro_placement_partial(
            bottom_die_macro_x: np.ndarray,
            bottom_die_macro_y: np.ndarray,
            bottom_die_macro_w: np.ndarray,
            bottom_die_macro_h: np.ndarray,
            upper_die_macro_x: np.ndarray,
            upper_die_macro_y: np.ndarray,
            upper_die_macro_w: np.ndarray,
            upper_die_macro_h: np.ndarray,
            xl: float,
            yl: float,
            xh: float,
            yh: float,
            figure_path: str,
            placed_bottom_indices: List[int],
            placed_upper_indices: List[int],
            dpi: int = 150,
            highlight_bottom_idx: Optional[int] = None,
            highlight_upper_idx: Optional[int] = None) -> str:
        """
        Plot 3D macro placement with two subplots, showing only placed macros.
        - Left: Bottom die macros (only placed ones)
        - Right: Upper die macros (only placed ones)
        
        Args:
            bottom_die_macro_x: Array of bottom die macro x coordinates (all macros)
            bottom_die_macro_y: Array of bottom die macro y coordinates (all macros)
            bottom_die_macro_w: Array of bottom die macro widths (all macros)
            bottom_die_macro_h: Array of bottom die macro heights (all macros)
            upper_die_macro_x: Array of upper die macro x coordinates (all macros)
            upper_die_macro_y: Array of upper die macro y coordinates (all macros)
            upper_die_macro_w: Array of upper die macro widths (all macros)
            upper_die_macro_h: Array of upper die macro heights (all macros)
            xl: Layout left boundary
            yl: Layout bottom boundary
            xh: Layout right boundary
            yh: Layout top boundary
            figure_path: Path to save the figure (required)
            placed_bottom_indices: List of bottom die macro indices that have been placed
            placed_upper_indices: List of upper die macro indices that have been placed
            dpi: DPI for saved figure
            highlight_bottom_idx: Optional index of bottom die macro to highlight (local index in placed list)
            highlight_upper_idx: Optional index of upper die macro to highlight (local index in placed list)
        
        Returns:
            figure_path: Path where the figure was saved
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(figure_path) if os.path.dirname(figure_path) else '.', exist_ok=True)
        
        # Create figure with 2 subplots
        fig, axes = plt.subplots(1, 2, figsize=(24, 12))
        
        # Plot 1: Bottom Die Macros (left subplot) - only placed ones
        ax1 = axes[0]
        ax1.set_xlim(xl, xh)
        ax1.set_ylim(yl, yh)
        ax1.set_aspect('equal')
        
        n_placed_bottom = len(placed_bottom_indices)
        for local_idx, global_idx in enumerate(placed_bottom_indices):
            if global_idx >= len(bottom_die_macro_x):
                continue
            x, y = float(bottom_die_macro_x[global_idx]), float(bottom_die_macro_y[global_idx])
            w, h = float(bottom_die_macro_w[global_idx]), float(bottom_die_macro_h[global_idx])
            # Skip invalid rectangles
            if w <= 0 or h <= 0 or not np.isfinite([x, y, w, h]).all():
                continue
            is_highlighted = (highlight_bottom_idx is not None and local_idx == highlight_bottom_idx)
            rect = Rectangle(
                (x, y), w, h,
                linewidth=3 if is_highlighted else 1,
                edgecolor='darkgreen' if is_highlighted else 'green',
                facecolor='yellow' if is_highlighted else 'lightgreen',
                alpha=0.9 if is_highlighted else 0.7
            )
            ax1.add_patch(rect)
        
        ax1.set_xlabel('X (microns)', fontsize=16)
        ax1.set_ylabel('Y (microns)', fontsize=16)
        title = f'Bottom Die Macros ({n_placed_bottom} placed)'
        if highlight_bottom_idx is not None:
            title += f' [Highlighted: macro {highlight_bottom_idx}]'
        ax1.set_title(title, fontsize=18)
        ax1.grid(True, linestyle='--', alpha=0.3)
        ax1.tick_params(labelsize=16)
        
        # Plot 2: Upper Die Macros (right subplot) - only placed ones
        ax2 = axes[1]
        ax2.set_xlim(xl, xh)
        ax2.set_ylim(yl, yh)
        ax2.set_aspect('equal')
        
        n_placed_upper = len(placed_upper_indices)
        for local_idx, global_idx in enumerate(placed_upper_indices):
            if global_idx >= len(upper_die_macro_x):
                continue
            x, y = float(upper_die_macro_x[global_idx]), float(upper_die_macro_y[global_idx])
            w, h = float(upper_die_macro_w[global_idx]), float(upper_die_macro_h[global_idx])
            # Skip invalid rectangles
            if w <= 0 or h <= 0 or not np.isfinite([x, y, w, h]).all():
                continue
            is_highlighted = (highlight_upper_idx is not None and local_idx == highlight_upper_idx)
            rect = Rectangle(
                (x, y), w, h,
                linewidth=3 if is_highlighted else 1,
                edgecolor='darkred' if is_highlighted else 'red',
                facecolor='yellow' if is_highlighted else 'lightcoral',
                alpha=0.9 if is_highlighted else 0.7
            )
            ax2.add_patch(rect)
        
        ax2.set_xlabel('X (microns)', fontsize=16)
        ax2.set_ylabel('Y (microns)', fontsize=16)
        title = f'Upper Die Macros ({n_placed_upper} placed)'
        if highlight_upper_idx is not None:
            title += f' [Highlighted: macro {highlight_upper_idx}]'
        ax2.set_title(title, fontsize=18)
        ax2.grid(True, linestyle='--', alpha=0.3)
        ax2.tick_params(labelsize=16)
        
        # Save figure
        plt.tight_layout()
        plt.savefig(figure_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        
        return figure_path
    
    @staticmethod
    def plot_single_die_macros(
            macro_x: np.ndarray,
            macro_y: np.ndarray,
            macro_w: np.ndarray,
            macro_h: np.ndarray,
            xl: float,
            yl: float,
            xh: float,
            yh: float,
            figure_path: str,
            die_type: str = 'bottom',
            hpwl_val: Optional[float] = None,
            title: Optional[str] = None,
            dpi: int = 150,
            highlight_idx: Optional[int] = None) -> str:
        """
        Plot macros for a single die (bottom or upper) without cells.
        Similar to place_3d_v2 visualization style.
        
        Args:
            macro_x: Array of macro x coordinates
            macro_y: Array of macro y coordinates
            macro_w: Array of macro widths
            macro_h: Array of macro heights
            xl: Layout left boundary
            yl: Layout bottom boundary
            xh: Layout right boundary
            yh: Layout top boundary
            figure_path: Path to save the figure (required)
            die_type: 'bottom' or 'upper' (default: 'bottom')
            hpwl_val: Current HPWL value (optional, for title)
            title: Custom title (optional, overrides auto-generated title)
            dpi: DPI for saved figure
            highlight_idx: Optional index of macro to highlight
        
        Returns:
            figure_path: Path where the figure was saved
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(figure_path) if os.path.dirname(figure_path) else '.', exist_ok=True)
        
        # Create figure and axis
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        
        # Set axis limits to layout boundaries
        ax.set_xlim(xl, xh)
        ax.set_ylim(yl, yh)
        ax.set_aspect('equal')
        
        # Determine colors based on die type
        if die_type == 'bottom':
            edgecolor_normal = 'green'
            edgecolor_highlight = 'darkgreen'
            facecolor_normal = 'lightgreen'
            facecolor_highlight = 'yellow'
            die_name = 'Bottom Die'
        else:
            edgecolor_normal = 'red'
            edgecolor_highlight = 'darkred'
            facecolor_normal = 'lightcoral'
            facecolor_highlight = 'yellow'
            die_name = 'Upper Die'
        
        # Draw each macro as a rectangle
        n_macros = len(macro_x)
        for i in range(n_macros):
            x, y = float(macro_x[i]), float(macro_y[i])
            w, h = float(macro_w[i]), float(macro_h[i])
            # Skip invalid rectangles
            if w <= 0 or h <= 0 or not np.isfinite([x, y, w, h]).all():
                continue
            is_highlighted = (highlight_idx is not None and i == highlight_idx)
            rect = Rectangle(
                (x, y), w, h,
                linewidth=3 if is_highlighted else 1,
                edgecolor=edgecolor_highlight if is_highlighted else edgecolor_normal,
                facecolor=facecolor_highlight if is_highlighted else facecolor_normal,
                alpha=0.9 if is_highlighted else 0.7
            )
            ax.add_patch(rect)
        
        # Set labels and title
        ax.set_xlabel('X (microns)', fontsize=16)
        ax.set_ylabel('Y (microns)', fontsize=16)
        
        if title is None:
            title = f'{die_name} Macros ({n_macros} macros)'
            if highlight_idx is not None:
                title += f' [Highlighted: macro {highlight_idx}]'
            if hpwl_val is not None:
                title += f' - HPWL: {hpwl_val:.2f}'
        
        ax.set_title(title, fontsize=18)
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.tick_params(labelsize=16)
        
        # Save figure
        plt.tight_layout()
        plt.savefig(figure_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        
        return figure_path

