C configure-flags: --f77binding

      subroutine testone(m_hidden, m, n, arr)
      implicit none
C     Assert that m_hidden == m + 1.
C     Then do arr = arange(m*n).reshape(m, n)
      integer :: m_hidden, m, n, i, j, idx
      real*8 :: arr(m_hidden, n)
      if (m_hidden /= m + 1) then
         write (*,*) 'assumption failed in pyf_support.f'
         arr = 0
      else
         idx = 0
         do i = 1, m_hidden
            do j = 1, n
               arr(i, j) = idx
               idx = idx + 1
            end do
         end do
      end if
      end subroutine
      
      subroutine reorders(x, y, z)
      implicit none
      integer x, z, i
      integer y(4)
      x = 1
      do i = 1, 4
         y(i) = 2
      enddo
      z = 3
      end subroutine

      function fort_sum_simple(n, arr)
      implicit none
      integer i, n
      real*8 fort_sum_simple
      real*8 arr(n)
      fort_sum_simple = 0
      do i = 1, n
         fort_sum_simple = fort_sum_simple + arr(i)
      enddo
      end function

      function fort_sum(n, arr)
      implicit none
      integer i, n
      real*8 fort_sum
      real*8 arr(n)
      fort_sum = 0
      do i = 1, n
         fort_sum = fort_sum + arr(i)
      enddo
      end function

      subroutine intent_copy_arange(x, n)
      implicit none
      integer n, i
      real*8 x(n)
      do i = 1, n
         x(i) = i
      enddo
      end subroutine

      subroutine intent_overwrite_arange(x, n)
      implicit none
      integer n, i
      real*8 x(n)
      do i = 1, n
         x(i) = i
      enddo
      end subroutine

      function sum_and_fill_optional_arrays(x, y, z, m, n)
      implicit none
      double precision x(m, n)
      complex*16 y(m, n)
      integer z(m, n)
      complex*16 sum_and_fill_optional_arrays
      integer i, j, m, n
      sum_and_fill_optional_arrays = (0d0, 0d0)
      do j = 1, n
         do i = 1, m
            sum_and_fill_optional_arrays = sum_and_fill_optional_arrays
     & + x(i, j) + y(i, j) + z(i, j)
            x(i, j) = 1.0
            y(i, j) = (2.0, 3.0)
            z(i, j) = 4
         enddo
      enddo
      end function

      function aux_arg(x, ch)
      implicit none
      integer x
      integer aux_arg
      character ch
      aux_arg = x
      end function

      function a_function(y)
      implicit none
      integer a_function
      integer y
      a_function = 13 + y
      end function

      subroutine sdefault(z)
      real z
      z = z * 2
      end subroutine

      subroutine cdefault(z)
      complex z
      z = z * 2
      end subroutine

      subroutine temparray(n, x, y)
      integer x(n), y(n)
      integer i, n
      do i = 1, n
         y(i) = x(i)
      enddo
      do i = 1, n
         x(i) = y(i) * 2
      enddo
      end subroutine
      
      subroutine alignment(n, a, b, c)
      integer n
      integer*4 a(n), b(n), c(n)
      end subroutine alignment
